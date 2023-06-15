*** Settings ***
Resource            qbrix/robot/QRobot.robot

Suite Setup         Run keyword    
...                    QRobot.Open Q Browser
Suite Teardown      QRobot.Close Q Browser


*** Test Cases ***
Validate Qbrix
    Validate Minimal Rowcount
    ...    Organization
    ...    1
    ...    continueonfail=True
    ...    datatag=Simple Query validation of the Organization Object
    #Validate With Testim    Validate_Hello_Login
