# Storage Account Provisioning Script
# Updated for planproof project

$rg = "planproof-dev-rg"
$location = "uksouth"
$stg = "planproofdevstg" + (Get-Random -Maximum 99999)

Write-Host "Resource Group: $rg"
Write-Host "Storage Account: $stg"
Write-Host "Location: $location"

# Resource group already exists, so skipping creation
# az group create -n $rg -l $location

az storage account create -g $rg -n $stg -l $location --sku Standard_LRS --kind StorageV2

$stgKey = (az storage account keys list -g $rg -n $stg --query "[0].value" -o tsv)

az storage container create --name "inbox" --account-name $stg --account-key $stgKey
az storage container create --name "artefacts" --account-name $stg --account-key $stgKey
az storage container create --name "logs" --account-name $stg --account-key $stgKey

Write-Host "Storage account created: $stg"
Write-Host "Containers created: inbox, artefacts, logs"


