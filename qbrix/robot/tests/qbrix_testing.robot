*** Settings ***
Resource            qbrix/robot/QRobot.robot

Suite Setup         Run keyword    QRobot.Open Q Browser    record_video=False
Suite Teardown      QRobot.Close Q Browser


*** Test Cases ***
#
# **TESTING NOTES**
#
# This is a test only robot file. Replace the keywords under Run Automation to test the task(s) you want to test.
#
# It is best to test them directly from terminal by running cci task run robot --org OrgAliasHere --suites qbrix/robot/tests/qbrix_testing.robot
#
# The above will allow you to see what the robot is doing and also generate a log of what is happening. See the output.xml file afterwards to help diagnose issues.
#
# Note: The default timeout for this is 900 seconds but if you have a long running process, ensure you change the value above next to "Set browser timeout" to something more suitable for the overall timeout for everything you are running.
#
Run Automation
    enable_custom_help_in_user_engagement
