# Wagtail A/B Testing

[![Version](https://img.shields.io/pypi/v/wagtail-ab-testing.svg?style=flat)](https://pypi.python.org/pypi/wagtail-ab-testing/)
[![License](https://img.shields.io/badge/license-BSD-blue.svg?style=flat)](https://opensource.org/licenses/BSD-3-Clause)
[![codecov](https://img.shields.io/codecov/c/github/torchbox/wagtail-ab-testing?style=flat)](https://codecov.io/gh/torchbox/wagtail-ab-testing)
[![Language grade: Python](https://img.shields.io/lgtm/grade/python/g/torchbox/wagtail-ab-testing.svg?logo=lgtm&logoWidth=18&style=flat)](https://lgtm.com/projects/g/torchbox/wagtail-ab-testing/context:python)

Wagtail A/B Testing is an A/B testing package for Wagtail that allows users to create and manage A/B tests on pages through the Wagtail admin.

Key features:

 - Create an A/B test on any page from within Wagtail
 - Tests using page revisions (no need to create separate pages for the variants)
 - It prevents users from editing the page while a test is in progress
 - Calculates confidence using a Pearson's chi-squared test

[Changelog](https://github.com/torchbox/wagtail-ab-testing/blob/main/CHANGELOG.md)

## Usage

### Creating an A/B test

Any user with the "Create A/B test" permission can create an A/B test by clicking "Save and create A/B test" from the page's action menu.

The first page shows the user the difference between the content in the latest draft against the live version of the page.
This allows them to check what changes on the page are going to be tested.

Once they've confirmed that, the user is taken to a form to insert the test name/hypothesis, select a goal, and sample size.

![Screenshot of Wagtail A/B Testing create page](/screenshot-create.png)

### Monitoring test progress

While the test is running, the page's edit view gets replaced with a dashboard showing the current test progress.
Users cannot edit the page until the test is completed or cancelled.

Any user with permission to publish the page can start, pause, resume or end A/B tests on that page.

![Screenshot of Wagtail A/B Testing](/screenshot.png)

### Finishing the test

The test stops automatically when the number of participants reaches the sample size.
Based on the results shown, a user must decide whether to publish the new changes or revert to the old version of the page.

Once they've chosen, the page edit view returns to normal.
The results from this A/B test remain accessible under the A/B testing tab or from the A/B testing report.

![Screenshot of Wagtail A/B Testing](/screenshot-finish.png)

## Installation

Firstly, install the ``wagtail-ab-testing`` package from PyPI:

    pip install wagtail-ab-testing

Then add it into ``INSTALLED_APPS``:

```python
INSTALLED_APPS = [
    # ...
    'wagtail_ab_testing',
    # ...
]
```

Then add the following to your URLconf:

```python
from wagtail_ab_testing import urls as ab_testing_urls

urlpatterns = [
    ...

    url(r'^abtesting/', include(ab_testing_urls)),
]
```

Finally, add the tracking script to your base HTML template:

```django+HTML
{# Insert this at the top of the template #}
{% load wagtail_ab_testing_tags %}

...

{# Insert this where you would normally insert a <script> tag #}
{% wagtail_ab_testing_script %}
```

## Goal events

Each A/B test has a goal that is measured after a user visits the page that the A/B test is running on.

The goal is defined by a destination page and and event type. For example, if the A/B test needs to measure how a change on the page affects the number of users who go on to submit a "Contact us" form, then the 'destination page' would be the "Contact us" page and the 'event type' would be "Submit form".

Out of the box, the only 'event type' that Wagtail A/B testing supports is visiting the destination page.
If you need to measure something else (such as submitting a form, purchasing something, or just clicking a link), you can implement a custom 'event type'.

### Implementing a custom goal event type

Custom event types are implemented for specific types of destination page.

Firstly, you need to register the 'event type' using the `register_ab_testing_event_types` hook,
this displays the goal 'event type' in the list of options when an A/B test is being created:


```python
# myapp/wagtail_hooks.py

from wagtail.core import hooks
from wagtail_ab_testing.events import BaseEvent


class CustomEvent(BaseEvent):
    name = "Name of the event type"
    requires_page = True  # Set to False to create a "Global" event type that could be reached on any page

    def get_page_types(self):
        return [
            # Return a list of page models that can be used as destination pages for this event type
            # For example, if this 'event type' is for a 'call to action' button that only appears on
            # the homepage, put your `HomePage` model here.
        ]


@hooks.register('register_ab_testing_event_types')
def register_submit_form_event_type():
    return {
        'slug-of-the-event-type': CustomEvent,
    }

```

Next you need to add logic in that logs a conversion when the user reaches that goal.
To do this, you can copy/adapt the following code snippet:

```python
# Check if the user is trackable
if request_is_trackable(request):
    # Check if the page is the goal of any running tests
    tests = AbTest.objects.filter(goal_event='slug-of-the-event-type', goal_page=the_page, status=AbTest.STATUS_RUNNING)
    for test in tests:
        # Is the user a participant in this test?
        if f'wagtail-ab-testing_{test.id}_version' not in request.session:
            continue

        # Has the user already completed the test?
        if f'wagtail-ab-testing_{test.id}_completed' in request.session:
            continue

        # Log a conversion
        test.log_conversion(request.session[f'wagtail-ab-testing_{test.id}_version'])
        request.session[f'wagtail-ab-testing_{test.id}_completed'] = 'yes'
```

#### Example: Adding a "Submit form" event type

In this example, we will add a "Submit form" event type for a ``ContactUsFormPage`` page type.

Firstly, we need to register the event type. To do this, implement a handler for the ``register_ab_testing_event_types`` hook in your app:

```python
# myapp/wagtail_hooks.py

from wagtail.core import hooks
from wagtail_ab_testing.events import BaseEvent

from .models import ContactUsFormPage


class SubmitFormPageEvent(BaseEvent):
    name = "Submit form page"

    def get_page_types(self):
        # Only allow this event type to be used if he user has
        # selected an instance of `ContactUsFormPage` as the goal
        return [
            ContactUsFormPage,
        ]


@hooks.register('register_ab_testing_event_types')
def register_submit_form_event_type():
    return {
        'submit-contact-us-form': SubmitFormPageEvent,
    }
```

This allows users to select the "Submit form page" event type when their goal page is set to any instance of ``ContactUsFormPage``.

Next, we need to add some code to record conversions for this event type.
To do this, we will customise the ``.render_landing_page()`` method that is inherited from the ``AbstractForm`` model.
This method is a view that returns the "thank you" page to the user. It's ideal for this use because user's will can
only get there by submitting the form, and we have the ``request`` object available which is required for some of the logic.:

```python
# myapp/models.py

from wagtail.contrib.forms.models import AbstractFormPage

from wagtail_ab_testing.models import AbTest
from wagtail_ab_testing.utils import request_is_trackable


class ContactUsFormPage(AbstractForm):

    def render_landing_page(self, request, *args, **kwargs):
        # Check if the user is trackable
        if request_is_trackable(request):
            # Check if submitting this form is the goal of any running tests
            tests = AbTest.objects.filter(goal_event='submit-contact-us-form', goal_page=self, status=AbTest.STATUS_RUNNING)
            for test in tests:
                # Is the user a participant in this test?
                if f'wagtail-ab-testing_{test.id}_version' not in request.session:
                    continue

                # Has the user already completed the test?
                if f'wagtail-ab-testing_{test.id}_completed' in request.session:
                    continue

                # Log a conversion
                test.log_conversion(request.session[f'wagtail-ab-testing_{test.id}_version'])
                request.session[f'wagtail-ab-testing_{test.id}_completed'] = 'yes'

        return super().render_landing_page(request, *args, **kwargs)
```

## Running A/B tests on a site that uses Cloudflare caching

To run Wagtail A/B testing on a site that uses Cloudflare, firstly generate a secure random string to use as a token, and configure that token in your Django settings file:

```python
WAGTAIL_AB_TESTING_WORKER_TOKEN = '<token here>'
```

Then set up a Cloudflare Worker based on the following JavaScript. Don't forget to set ``WAGTAIL_DOMAIN``:

```javascript
// Set this to the domain name of your backend server
const WAGTAIL_DOMAIN = "mysite.herokuapp.com";

// Set to false if Cloudflare shouldn't automatically redirect requests to use HTTPS
const ENFORCE_HTTPS = true;

async function handleRequest(request) {
  const url = new URL(request.url)

  if (url.protocol == 'http:' && ENFORCE_HTTPS) {
    url.protocol = 'https:';
    return Response.redirect(url, 301);
  }

  if (request.method === 'GET') {
    const newRequest = new Request(request, {
      headers: {
        ...request.headers,
        'Authorization': 'Token ' + WAGTAIL_AB_TESTING_WORKER_TOKEN,
        'X-Requested-With': 'WagtailAbTestingWorker'
      }
    });

    url.hostname = WAGTAIL_DOMAIN;
    response = await fetch(url.toString(), newRequest);

    // If there is a test running at the URL, the worker would return
    // a JSON response containing both versions of the page. Also, it
    // returns the test ID in the X-WagtailAbTesting-Test header.
    const testId = response.headers.get('X-WagtailAbTesting-Test');
    if (testId) {
      // Participants of a test would have a cookie that tells us which
      // version of the page being tested on that they should see
      // If they don't have this cookie, serve a random version
      const versionCookieName = `abtesting-${testId}-version`;
      const cookie = request.headers.get('cookie');
      let version;
      if (cookie && cookie.includes(`${versionCookieName}=control`)) {
        version = 'control';
      } else if (cookie && cookie.includes(`${versionCookieName}=variant`)) {
        version = 'variant';
      } else if (Math.random() < 0.5) {
        version = 'control';
      } else {
        version = 'variant';
      }

      return response.json().then(json => {
        return new Response(json[version], {
          headers: {
            ...response.headers,
            'Content-Type': 'text/html'
          }
        });
      });
    }

    return response;
  } else {
    return await fetch(url.toString(), request);
  }
}

addEventListener('fetch', event => {
  event.respondWith(handleRequest(event.request));
});
```

Add a variable to the worker called ``WAGTAIL_AB_TESTING_WORKER_TOKEN`` giving it the same token value that you generated earlier.

Finally, add a route into Cloudflare so that it routes all traffic through this worker.
