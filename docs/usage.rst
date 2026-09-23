Usage
=====

Local evaluation
----------------

Create or activate the project virtual environment, then run the tests and the
local demonstration:

.. code-block:: powershell

   .\vehicleenv\Scripts\Activate.ps1
   python -m pytest
   python -m src.local_demo

The local demonstration evaluates one event and prints an alert JSON object.
It does not create AWS clients or send an email.

Change the temperature threshold
---------------------------------

The default threshold is 85 degrees Celsius. To change it for one local
PowerShell session, set ``TEMPERATURE_THRESHOLD`` before running the demo:

.. code-block:: powershell

   $env:TEMPERATURE_THRESHOLD = "90"
   python -m src.local_demo

The same setting is applied to a deployed Lambda function through the
Terraform variable:

.. code-block:: powershell

   terraform -chdir=terraform apply -var="temperature_threshold=90"

Changing the threshold to 90 means an event at 90 degrees or above creates a
high-temperature alert.

AWS processing flow
-------------------

In AWS, telemetry follows this path:

.. code-block:: text

   flowchart LR
       Producer[Telemetry producer] --> Queue[SQS telemetry queue]
       Queue --> Lambda[Lambda alert handler]
       Lambda --> SNS[SNS alert topic]
       Lambda --> S3[S3 audit bucket]
       SNS --> Email[Confirmed email subscription]

The batch file in the project root can be submitted directly to the deployed
SQS queue from PowerShell:

.. code-block:: powershell

   aws sqs send-message-batch `
     --queue-url "<queue-url>" `
     --entries file://bulk-messages.json

The email subscription must be confirmed before SNS can deliver notifications.

Send one event without the batch JSON file
-------------------------------------------

For a one-off test, create the SQS message body directly in PowerShell and
send it with ``aws sqs send-message``. This example creates one alert because
the temperature is 90 degrees Celsius:

.. code-block:: powershell

    $body = '{"event_id":"manual-001","vehicle_id":"BMW-MANUAL-001","timestamp":"2026-09-23T12:00:00Z","temperature":90,"fault_code":null}'
    aws sqs send-message `
       --queue-url "<queue-url>" `
       --message-body $body

To test a normal event, use a temperature below the threshold and no critical
fault code:

.. code-block:: powershell

    $body = '{"event_id":"manual-002","vehicle_id":"BMW-MANUAL-002","timestamp":"2026-09-23T12:01:00Z","temperature":70,"fault_code":null}'
    aws sqs send-message `
       --queue-url "<queue-url>" `
       --message-body $body

Find the queue URL
------------------

The queue URL is created by Terraform when the ``aws_sqs_queue.telemetry``
resource is deployed. The easiest ways to find it are:

* Terraform output: ``terraform -chdir=terraform output telemetry_queue_url``
* AWS CLI: ``aws sqs get-queue-url --queue-name bmw-vehicle-telemetry``
* AWS Console: open **SQS**, select the **bmw-vehicle-telemetry** queue, and
   copy the **Queue URL** shown in the queue details.

The queue URL is different from the SNS topic ARN. Use the SQS queue URL with
``send-message`` or ``send-message-batch``.

Alert behavior
--------------

An event creates an alert when either condition is true:

* ``temperature >= TEMPERATURE_THRESHOLD``
* ``fault_code`` is listed in ``CRITICAL_FAULT_CODES``

Normal events are counted but do not publish an SNS message or write an S3
record. Invalid events are logged and re-raised so Lambda and SQS retry and
dead-letter behavior can handle them.
