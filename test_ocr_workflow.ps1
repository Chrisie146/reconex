# Test OCR Workflow End-to-End
Write-Host "=== Testing OCR Workflow ===" -ForegroundColor Green

# Use a test session ID
$sessionId = [guid]::NewGuid().ToString()
Write-Host "Session ID: $sessionId" -ForegroundColor Cyan

# 1. Test /ocr/regions endpoint with sample regions
Write-Host "`n[1] Testing POST /ocr/regions..." -ForegroundColor Yellow

$regionPayload = @{
    pages = @{
        "1" = @{
            date_region = @{ x = 0.05; y = 0.1; w = 0.15; h = 0.8 }
            description_region = @{ x = 0.2; y = 0.1; w = 0.5; h = 0.8 }
            amount_region = @{ x = 0.75; y = 0.1; w = 0.2; h = 0.8 }
        }
    }
    amount_type = "single"
} | ConvertTo-Json -Depth 3

try {
    $regionsResponse = Invoke-RestMethod -Uri "http://127.0.0.1:8000/ocr/regions?session_id=$sessionId" `
        -Method Post `
        -Body $regionPayload `
        -ContentType "application/json"
    Write-Host "✅ Regions saved:" -ForegroundColor Green
    Write-Host $regionsResponse | ConvertTo-Json -Depth 2
} catch {
    Write-Host "❌ Failed to save regions:" -ForegroundColor Red
    Write-Host $_.Exception.Message
    exit 1
}

# 2. Test /ocr/extract endpoint with sample PDF
Write-Host "`n[2] Testing POST /ocr/extract..." -ForegroundColor Yellow

$pdfPath = "C:\Users\christopherm\statementbur_python\FNB_ASPIRE_CURRENT_ACCOUNT_1332.pdf"
if (!(Test-Path $pdfPath)) {
    Write-Host "❌ Sample PDF not found: $pdfPath" -ForegroundColor Red
    exit 1
}

try {
    # Create multipart form data
    $boundary = "----FormBoundary" + [guid]::NewGuid().ToString("N")
    $fileContent = [System.IO.File]::ReadAllBytes($pdfPath)
    $fileName = [System.IO.Path]::GetFileName($pdfPath)

    # Build multipart content
    $multipartContent = @()
    $multipartContent += "--$boundary"
    $multipartContent += "Content-Disposition: form-data; name=`"file`"; filename=`"$fileName`""
    $multipartContent += "Content-Type: application/pdf"
    $multipartContent += ""
    $multipartContent += [System.Text.Encoding]::UTF8.GetString($fileContent)
    $multipartContent += "--$boundary--"
    $multipartContent += ""

    $body = $multipartContent -join "`r`n"

    $extractResponse = Invoke-RestMethod -Uri "http://127.0.0.1:8000/ocr/extract?session_id=$sessionId" `
        -Method Post `
        -Body $body `
        -ContentType "multipart/form-data; boundary=$boundary" `
        -TimeoutSec 30

    Write-Host "✅ OCR extraction completed:" -ForegroundColor Green
    Write-Host "Results keys: $($extractResponse.results.Keys -join ', ')"
    if ($extractResponse.results -and $extractResponse.results[1]) {
        Write-Host "Page 1 rows: $($extractResponse.results[1].rows.Count)"
        Write-Host "Page 1 warnings: $($extractResponse.results[1].warnings.Count)"
        if ($extractResponse.results[1].rows.Count -gt 0) {
            Write-Host "`nFirst row (if exists):"
            $extractResponse.results[1].rows[0] | ConvertTo-Json
        } else {
            Write-Host "(No rows extracted - may need adjustment to region coordinates)"
        }
    }
} catch {
    Write-Host "❌ Failed to extract OCR:" -ForegroundColor Red
    Write-Host $_.Exception.Message
    exit 1
}

Write-Host "`n=== ✅ All tests passed! ===" -ForegroundColor Green
Write-Host "Frontend: http://127.0.0.1:3000/ocr" -ForegroundColor Cyan
Write-Host "Backend API: http://127.0.0.1:8000" -ForegroundColor Cyan
