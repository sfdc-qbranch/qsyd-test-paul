*** Settings ***
Resource            qbrix/robot/QRobot.robot
Suite Setup         Run keyword    
...                    QRobot.Open Q Browser
Suite Teardown      QRobot.Close Q Browser


*** Test Cases ***
#
# **NOTES**
#
# Each test should be added to an existing test case or a new test case. These can then be referenced by a task in the cumulusci.yml file.
#
# All Tests have been organised into different products or shared if they are non specific or cross multiple products. Please add new tests to the relevant sections below.
#
# -----------------------------------------------------------------------------------------------------------------------------------------
# SHARED TESTS
# -----------------------------------------------------------------------------------------------------------------------------------------
Check and Enable Contacts to Multiple Accounts
    Enable Contacts to Multiple Accounts

Set Org Wide Email Address
    Set Org Wide Email

Disable MFA in Org
    Disable MFA

Enable Custom Help
    enable_custom_help_in_user_engagement

Enable Data Pipelines
    enable_data_pipelines
#
# -----------------------------------------------------------------------------------------------------------------------------------------
# EINSTEIN TESTS
# -----------------------------------------------------------------------------------------------------------------------------------------

Run Automation to check and Enable Einstein TCRM
    Enable Einstein Analytics CRM

Run Automation to Check and Enable Einstein Insights
    Go To Campaign Insights Setup Page
    Set Lightning Toggle    on
    Go To Opportunity Insights Setup Page
    Set Lightning Toggle    on
    Go To Account Insights Setup Page
    Set Lightning Toggle    on
    Go To Key Account Insights Setup Page
    Set Lightning Toggle    on

Run Automation to check and enable Campaign Insights
    Go To Campaign Insights Setup Page
    Set Lightning Toggle    on

Check and Enable Prediction Builder
    Enable Einstein Prediction Builder

Check and Enable Einstein Forecasting
    Enable Einstein Forecasting

Check and Enable Oppty Scoring
    Go To Oppty Scoring Setup page

Check and Enable Lead Scoring
    Go To Lead Scoring Setup page

Check and Enable Automated Data Capture
    Enable Automated Data Capture

Check and Enable Call Coaching ECI
    Enable Call Coaching ECI

Check and Setup Einstein Article Recommendations
    Einstein Article Recommendations Setup
#
# -----------------------------------------------------------------------------------------------------------------------------------------
# FIELD SERVICE TESTS
# -----------------------------------------------------------------------------------------------------------------------------------------

Check and Enable Field Service
    Enable Field Service

Check Enable and Update Field Service Permission Sets
    Enable All Field Service Permission Sets

Check and Disable Field Service Integration
    Disable Field Service Integration

Check and Disable Field Service Status Transitions
    Disable Field Service Status Transitions

Create Rider Chat Button
    Create A Chat Button And Automated Invitations    SFS - Rider Bot    SDO_SFS_Rider_Bot

Create Tracker Chat Button
    Create A Chat Button And Automated Invitations    SFS - Tracker Bot    SDO_SFS_Tracker_Bot

Create Felix Chat Button
    Create A Chat Button And Automated Invitations    HLS - Felix Bot      HLS_Felix_Bot

Create Mackie Chat Button
    Create A Chat Button And Automated Invitations    HLS - Mackie Bot      HLS_Mackie_Bot

Create Heka Chat Button
    Create A Chat Button And Automated Invitations    HLS - Heka Bot      HLS_Heka_Bot
    
Add Case Wrap Up Model
    Enable Einstein Classification
    Add Case Wrap Up Model

Add Case Classification Model
    Enable Einstein Classification
    Create Case Classification Model

#
# -----------------------------------------------------------------------------------------------------------------------------------------
# MARKETING TESTS
# -----------------------------------------------------------------------------------------------------------------------------------------

Check and Setup Pardot Connected App
    Enable Pardot App

Check and Enable Pardot
    Enable Pardot Setting

Check and Create Pardot Email Template
    Create Pardot Template
#
# -----------------------------------------------------------------------------------------------------------------------------------------
# SALES CLOUD TESTS
# -----------------------------------------------------------------------------------------------------------------------------------------

Run Automation to Enable Sales Engagement
    Enable Sales Engagement

Run Automation to Enable Sales Agreements
    Enable Sales Agreements

Run Automation to Check and Enable Forecasts
    Enable Forecasts

Set Guest API Access for Standard Channel Menu
    Set Guest on Channel Menu    SDO_Standard_Channel_Menu

Check and Update Forecast Hiararchy Settings
    Update Forecast Hierarchy Settings

Check and Enable Opportunity Splits
    Enable Opportunity Splits

Enable Sales Agreements
    Enable Sales Agreements

Messaging Components Setup
    Messaging Components Setup
#
# -----------------------------------------------------------------------------------------------------------------------------------------
# SERVICE CLOUD TESTS
# -----------------------------------------------------------------------------------------------------------------------------------------

Check and Enable Incident Management
    Enable Incident Management

Check and Enable Case Swarming
    Enable Case Swarming

Create Service Chat Buttons
    Create A Chat Button And Automated Invitations    *Standard Chat Button    SDO_Service_Chat
    Create A Chat Button And Automated Invitations    Service - Sunny Bot    SDO_Service_Sunny_Bot

Create Gl1tch Chat Button
    Create A Chat Button And Automated Invitations    Service - Gl1tch Bot    SDO_Service_Glitch_Bot

Create Manny Chat Button
    Create A Chat Button And Automated Invitations    MFG - Manny Bot    MFG_Service_Manny_Bot

Create Stellar Chat Button
    Create A Chat Button And Automated Invitations    Media - Stellar Bot    MDA_Stellar_Bot
#
# -----------------------------------------------------------------------------------------------------------------------------------------
# Q BRANCH TOOLING TESTS
# -----------------------------------------------------------------------------------------------------------------------------------------

Run Automation to check that Q Passport is configured
    Enable Q Passport

Check and Enable Q Tooling
    Enable Q Passport
    Enable Demo Boost
    Enable Demo Wizard
    Enable Data Tool
#
# -----------------------------------------------------------------------------------------------------------------------------------------
# Marketing CLOUD TESTS
# -----------------------------------------------------------------------------------------------------------------------------------------

Check and Enable Territory Management
    Enable Territory Management
#
# -----------------------------------------------------------------------------------------------------------------------------------------
# Net Zero Cloud TESTS
# -----------------------------------------------------------------------------------------------------------------------------------------

Check and Enable Net Zero Cloud
    Enable Net Zero
#
# -----------------------------------------------------------------------------------------------------------------------------------------
# VRA TESTS
# -----------------------------------------------------------------------------------------------------------------------------------------

Check and Create VRA Service Channel
    Create VRA Service Channel
#
# -----------------------------------------------------------------------------------------------------------------------------------------
# Chat Button
# -----------------------------------------------------------------------------------------------------------------------------------------

Chat Buttons and Automated Invitations
    Create Chat Button and Automated Invitations
# -----------------------------------------------------------------------------------------------------------------------------------------
# SCHEDULER TESTS
# -----------------------------------------------------------------------------------------------------------------------------------------

Check and Enable Scheduler Setting
    Enable Scheduler

Create Scheduler Service Chat Buttons
    Create A Chat Button And Automated Invitations    Scheduler - Chronos    SDO_Scheduler_Chronos_Bot

Check and Create Appointment Assignment Polcies
    Create Appointment Assignment Policies

Create Chronos Chat Button
    Create A Chat Button And Automated Invitations    Scheduler - Chronos    SDO_Scheduler_Chronos_Bot
# -----------------------------------------------------------------------------------------------------------------------------------------
# Survey Setup
# -----------------------------------------------------------------------------------------------------------------------------------------

Set Survey Default Community
    Set Survey Default Community    SDO - Consumer
# -----------------------------------------------------------------------------------------------------------------------------------------
# Service Presence Statuses to Profile
# -----------------------------------------------------------------------------------------------------------------------------------------

Add Service Presence Statuses to Profile
    Add Service Presence Statuses to Profile    System Administrator    All - Available
    Add Service Presence Statuses to Profile    System Administrator    Busy
    Add Service Presence Statuses to Profile    System Administrator    Busy - Break
    Add Service Presence Statuses to Profile    System Administrator    Busy - Lunch
    Add Service Presence Statuses to Profile    System Administrator    Busy - Training
    Add Service Presence Statuses to Profile    System Administrator    Cases - Available
    Add Service Presence Statuses to Profile    System Administrator    Chat - Available
    Add Service Presence Statuses to Profile    System Administrator    Messaging - Available
    Add Service Presence Statuses to Profile    System Administrator    Phone - Available

# -----------------------------------------------------------------------------------------------------------------------------------------
# Chat Agent Configurations
# -----------------------------------------------------------------------------------------------------------------------------------------

Add Profile to Chat Agent Configuration
    Add Profile To Chat Configuration    Chat Representatives    System Administrator
    Add Profile To Chat Configuration    Chat Representatives    SDO-Service

# -----------------------------------------------------------------------------------------------------------------------------------------
# Apex Operations
# -----------------------------------------------------------------------------------------------------------------------------------------

Apex Classes Compile
    Compile All Apex    300

# -----------------------------------------------------------------------------------------------------------------------------------------
# Manufacturing & Automotive Cloud Operations
# -----------------------------------------------------------------------------------------------------------------------------------------

Enable Manufacturing Service Console
    Enable Manufacturing Service Console

Enable Automotive Cloud Setting
    Enable Automotive Cloud Setting

Enable Automotive Cloud Service Console Setting
    Enable Automotive Cloud Service Console Setting

Enable Group Membership
    Enable Group Membership

Enable Account Manager Targets
    Enable Account Manager Targets

Enable Partner Visit Management
    Enable Partner Visit Management

Enable Partner Performance Management
    Enable Partner Performance Management

Enable Partner Lead Management
    Enable Partner Lead Management

Enable Program Based Business
    Enable Program Based Business

Enable Warranty Lifecycle Management
    Enable Warranty Lifecycle Management

Set Guest API Access for MFG Channel Menu
    Set Guest on Channel Menu    MFG_Service_Community_Channel

# -----------------------------------------------------------------------------------------------------------------------------------------
# FINANCIAL SERVICES Cloud Operations
# -----------------------------------------------------------------------------------------------------------------------------------------

Enable Interest Tagging
    Enable Interest Tagging

Enable Record Alert Access
    Enable Record Alert Access

Enable Business Rules Engine
    Enable Business Rules Engine

Enable Financial Account Setting
    Enable Financial Account Setting

Enable Actionable Segmentation Settings
    Enable Actionable Segmentation Settings

# -----------------------------------------------------------------------------------------------------------------------------------------
# NON PROFIT NGO Cloud Operations
# -----------------------------------------------------------------------------------------------------------------------------------------

Enable Program Benefits
    Enable Program Benefits

# -----------------------------------------------------------------------------------------------------------------------------------------
# HealthCare Cloud Operations
# -----------------------------------------------------------------------------------------------------------------------------------------

Enable Care Plans
    Enable Care Plans

Enable Care Plans Grantmaking
    Enable Care Plans Grantmaking

Enable Assessments
    Enable Assessments


# -----------------------------------------------------------------------------------------------------------------------------------------
# OmniStudio Settings
# -----------------------------------------------------------------------------------------------------------------------------------------
OmniStudio Settings Activation
    Activate Omnistudio Metadata
    
Standard OmniStudio Runtime Activation
    Activate Standard OmniStudio Runtime

Standard OmniStudio Runtime Deactivation
    Deactivate Standard OmniStudio Runtime

DataRaptor Versioning Activation
    Activate DataRaptor Versioning

DataRaptor Versioning Deactivation
    Deactivate DataRaptor Versioning

# -----------------------------------------------------------------------------------------------------------------------------------------
# Documnet Generation Settings
# -----------------------------------------------------------------------------------------------------------------------------------------
DocGen Setup
    Docgen Client Side Setup