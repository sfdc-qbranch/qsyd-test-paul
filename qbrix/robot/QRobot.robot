*** Settings ***

# CORE ROBOT LIBRARIES
Library     Browser
Library     Collections
Library     OperatingSystem
Library     String

# CUMULUSCI INTEGRATION LIBRARY
Library     cumulusci.robotframework.CumulusCI    ${ORG}

# CORE Q ROBOT
Library     qbrix/robot/QRobot.py
Library     qbrix/robot/QbrixSharedKeywords.py
Library     qbrix/robot/QbrixValidationKeywords.py

# CORE - Q BRANCH
Library     qbrix/robot/QbrixToolingKeywords.py

# PRODUCT - SHARED PLATFORM LIBRARIES
Library     qbrix/robot/QbrixCMS.py
Library     qbrix/robot/QbrixEinsteinKeywords.py
Library     qbrix/robot/QbrixSchedulerKeywords.py
Library     qbrix/robot/QbrixSurveysKeywords.py

# PRODUCT - MARKETING
Library     qbrix/robot/QbrixMarketingKeywords.py

# PRODUCT - SALES CLOUD
Library     qbrix/robot/QbrixSalesCloudKeywords.py

# PRODUCT - SERVICE CLOUD AND SFS
Library     qbrix/robot/QbrixServiceKeywords.py
Library     qbrix/robot/QbrixFieldServiceKeywords.py
Library     qbrix/robot/QbrixVraKeywords.py

# INDUSTRY - COMMERCE CLOUD
Library     qbrix/robot/QbrixB2BKeywords.py

# INDUSTRY - FINS
Library     qbrix/robot/QbrixFINSKeywords.py

# INDUSTRY - MFG
Library     qbrix/robot/QbrixManufacturingKeywords.py

# INDUSTRY - NET ZERO CLOUD
Library     qbrix/robot/QbrixNetZeroKeywords.py

# INDUSTRY - NON PROFIT CLOUD (NGO)
Library     qbrix/robot/QbrixNGOKeywords.py

# INDUSTRY - Healthcare Cloud
Library     qbrix/robot/QbrixHLSKeywords.py

# INDUSTRY - OmniStudio
Library     qbrix/robot/QbrixDPAKeywords.py








