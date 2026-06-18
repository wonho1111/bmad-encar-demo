# Gemini 임베딩 차원 확인용 1회성 점검 스크립트
# 사용법: powershell -ExecutionPolicy Bypass -File check-embedding-dim.ps1 -Key "<API키>"
param(
    [Parameter(Mandatory = $true)]
    [string]$Key,
    [int]$Dim = 768
)

$ErrorActionPreference = "Stop"
[Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12

$uri = "https://generativelanguage.googleapis.com/v1beta/models/gemini-embedding-001:embedContent"
$headers = @{ "x-goog-api-key" = $Key }
$body = "{""content"":{""parts"":[{""text"":""white SUV""}]},""outputDimensionality"":$Dim}"

try {
    $r = Invoke-RestMethod -Uri $uri -Method Post -Headers $headers -ContentType "application/json" -Body $body
    Write-Output ("임베딩 차원: " + $r.embedding.values.Count)
}
catch {
    Write-Output "오류 발생 — 키가 올바른지 확인하세요."
    Write-Output $_.Exception.Message
}
