param(
    [string]$BackendUrl = "http://localhost:8080",
    [string]$DifyUrl = "http://localhost:8088",
    [int]$TimeoutSeconds = 120,
    [int]$IntervalSeconds = 3
)

$ErrorActionPreference = "Stop"

function Wait-HttpReady {
    param(
        [string]$Name,
        [string]$Url,
        [scriptblock]$Validate
    )

    $deadline = (Get-Date).AddSeconds($TimeoutSeconds)
    $lastError = "Noch keine Antwort"

    while ((Get-Date) -lt $deadline) {
        try {
            $response = Invoke-WebRequest `
                -Uri $Url `
                -MaximumRedirection 5 `
                -TimeoutSec 10 `
                -UseBasicParsing

            if (& $Validate $response) {
                Write-Host "[bereit] $Name - $Url"
                return
            }

            $lastError = "HTTP $($response.StatusCode), Inhalt noch nicht bereit"
        }
        catch {
            $lastError = $_.Exception.Message
        }

        Start-Sleep -Seconds $IntervalSeconds
    }

    throw "$Name war nach $TimeoutSeconds Sekunden nicht bereit: $lastError"
}

Wait-HttpReady `
    -Name "Application-Assistant-Backend" `
    -Url "$BackendUrl/health" `
    -Validate {
        param($response)
        if ($response.StatusCode -ne 200) {
            return $false
        }

        try {
            $body = $response.Content | ConvertFrom-Json
            return $body.status -eq "ok" -and `
                $body.service -eq "application-assistant-backend"
        }
        catch {
            return $false
        }
    }

Wait-HttpReady `
    -Name "Dify-Anmeldeseite" `
    -Url "$DifyUrl/signin" `
    -Validate {
        param($response)
        if ($response.StatusCode -ne 200) {
            return $false
        }

        $content = [string]$response.Content
        return $content.Length -gt 500 -and `
            $content -match "<html|<!DOCTYPE" -and `
            $content -match "_next/static|signin|Sign in"
    }

Write-Host "Alle lokalen Oberflächen sind bereit."
