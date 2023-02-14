*** Settings ***
Library     RequestsLibrary


*** Variables ***
${OCTOPOES_URI}         http://localhost:29000
${OCTOPOES_ORG_URI}     http://localhost:29000/_dev


*** Test Cases ***
Health Endpoint
    ${response}    Get    ${OCTOPOES_URI}/health
    Should Be Equal As Strings    ${response.status_code}    200
