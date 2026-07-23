<#
.SYNOPSIS
    ezcam 설치 폴더 구조를 스캔하여 텍스트/JSON 리포트로 저장합니다. (캡처 아님)

.DESCRIPTION
    지정한 경로(기본: C:\ezcam\1.1_1.1)의 전체 폴더/파일 목록을 스캔하여
    - 사람이 읽기 좋은 트리(scan_report.txt)
    - 기계가 읽기 좋은 JSON(scan_report.json)
    두 파일로 출력합니다.

    특히 다음 세 가지 질문에 답하도록 요약을 함께 만듭니다.
      1) 설치 폴더 바로 아래에 무엇이 있는지 (exe/dll/txt 등)
      2) resource\ 안에 docs 외에 무엇이 있는지 (templates/scripts/plugins/postprocessors 등)
      3) resource\docs 안에 언어 폴더(en/ja/ko/zh 등)가 있는지

.EXAMPLE
    powershell -ExecutionPolicy Bypass -File .\scan_folder.ps1

.EXAMPLE
    powershell -ExecutionPolicy Bypass -File .\scan_folder.ps1 -Root "C:\ezcam\1.1_1.1" -MaxDepth 6
#>

param(
    [string]$Root = "C:\ezcam\1.1_1.1",
    [int]$MaxDepth = 6,
    [string]$OutDir = "."
)

$ErrorActionPreference = "Stop"

if (-not (Test-Path -LiteralPath $Root)) {
    Write-Host "[오류] 경로를 찾을 수 없습니다: $Root" -ForegroundColor Red
    Write-Host "       -Root 인자로 올바른 설치 경로를 지정하세요." -ForegroundColor Yellow
    exit 1
}

$Root = (Resolve-Path -LiteralPath $Root).Path
$OutDir = (Resolve-Path -LiteralPath $OutDir).Path
$txtPath = Join-Path $OutDir "scan_report.txt"
$jsonPath = Join-Path $OutDir "scan_report.json"

Write-Host "스캔 시작: $Root" -ForegroundColor Cyan

# ---- 전체 항목 수집 (에러는 무시하고 접근 가능한 것만) ----
$allItems = Get-ChildItem -LiteralPath $Root -Recurse -Force -ErrorAction SilentlyContinue

# ---- 사람이 읽는 트리 만들기 ----
$rootDepth = ($Root.TrimEnd('\') -split '\\').Count
$treeLines = New-Object System.Collections.Generic.List[string]
$treeLines.Add("SCAN ROOT : $Root")
$treeLines.Add("SCAN TIME : $(Get-Date -Format 'yyyy-MM-dd HH:mm:ss')")
$treeLines.Add("=" * 70)

foreach ($item in ($allItems | Sort-Object FullName)) {
    $depth = (($item.FullName -split '\\').Count) - $rootDepth
    if ($depth -gt $MaxDepth) { continue }
    $indent = "  " * $depth
    if ($item.PSIsContainer) {
        $treeLines.Add("$indent[$($item.Name)]/")
    } else {
        $sizeKB = [math]::Round($item.Length / 1KB, 1)
        $treeLines.Add("$indent- $($item.Name)  ($sizeKB KB)")
    }
}

# ---- 요약: 확장자별 개수 ----
$extSummary = $allItems |
    Where-Object { -not $_.PSIsContainer } |
    Group-Object { if ($_.Extension) { $_.Extension.ToLower() } else { "(none)" } } |
    Sort-Object Count -Descending |
    ForEach-Object { [PSCustomObject]@{ ext = $_.Name; count = $_.Count } }

# ---- 질문 1: 루트 바로 아래 항목 ----
$topLevel = Get-ChildItem -LiteralPath $Root -Force -ErrorAction SilentlyContinue |
    ForEach-Object {
        [PSCustomObject]@{
            name  = $_.Name
            type  = if ($_.PSIsContainer) { "dir" } else { "file" }
            sizeKB = if ($_.PSIsContainer) { $null } else { [math]::Round($_.Length / 1KB, 1) }
        }
    }

# ---- 질문 2: resource\ 바로 아래 ----
$resourcePath = Join-Path $Root "resource"
$resourceChildren = @()
if (Test-Path -LiteralPath $resourcePath) {
    $resourceChildren = Get-ChildItem -LiteralPath $resourcePath -Force -ErrorAction SilentlyContinue |
        ForEach-Object {
            [PSCustomObject]@{
                name = $_.Name
                type = if ($_.PSIsContainer) { "dir" } else { "file" }
            }
        }
}

# ---- 질문 3: resource\docs 안 언어 폴더 ----
$docsPath = Join-Path $resourcePath "docs"
$docsChildren = @()
$langFolders = @()
$knownLangs = @("en", "en-us", "ja", "jp", "ko", "kr", "zh", "zh-cn", "zh-tw", "cn", "de", "fr", "es")
if (Test-Path -LiteralPath $docsPath) {
    $docsChildren = Get-ChildItem -LiteralPath $docsPath -Force -ErrorAction SilentlyContinue |
        ForEach-Object {
            [PSCustomObject]@{
                name = $_.Name
                type = if ($_.PSIsContainer) { "dir" } else { "file" }
            }
        }
    $langFolders = $docsChildren |
        Where-Object { $_.type -eq "dir" -and $knownLangs -contains $_.name.ToLower() } |
        Select-Object -ExpandProperty name
}

# ---- 요약 텍스트 블록 ----
$treeLines.Add("")
$treeLines.Add("=" * 70)
$treeLines.Add("요약 (SUMMARY)")
$treeLines.Add("=" * 70)
$treeLines.Add("총 폴더 수 : $(($allItems | Where-Object { $_.PSIsContainer }).Count)")
$treeLines.Add("총 파일 수 : $(($allItems | Where-Object { -not $_.PSIsContainer }).Count)")
$treeLines.Add("")
$treeLines.Add("[1] 루트 바로 아래:")
foreach ($t in $topLevel) { $treeLines.Add("    - $($t.name) ($($t.type))") }
$treeLines.Add("")
$treeLines.Add("[2] resource\ 바로 아래:")
if ($resourceChildren.Count -gt 0) {
    foreach ($r in $resourceChildren) { $treeLines.Add("    - $($r.name) ($($r.type))") }
} else {
    $treeLines.Add("    (resource 폴더 없음 또는 접근 불가)")
}
$treeLines.Add("")
$treeLines.Add("[3] resource\docs 안 언어 폴더:")
if ($langFolders.Count -gt 0) {
    $treeLines.Add("    발견된 언어 폴더: $($langFolders -join ', ')")
} else {
    $treeLines.Add("    (알려진 언어 폴더 없음)")
    $treeLines.Add("    docs 하위 항목:")
    foreach ($d in $docsChildren) { $treeLines.Add("      - $($d.name) ($($d.type))") }
}
$treeLines.Add("")
$treeLines.Add("확장자별 파일 개수:")
foreach ($e in $extSummary) { $treeLines.Add("    $($e.ext) : $($e.count)") }

# ---- 파일로 저장 ----
$treeLines -join "`r`n" | Out-File -LiteralPath $txtPath -Encoding UTF8

$report = [PSCustomObject]@{
    scanRoot         = $Root
    scanTime         = (Get-Date -Format "yyyy-MM-dd HH:mm:ss")
    totalDirs        = ($allItems | Where-Object { $_.PSIsContainer }).Count
    totalFiles       = ($allItems | Where-Object { -not $_.PSIsContainer }).Count
    topLevel         = $topLevel
    resourceChildren = $resourceChildren
    docsChildren     = $docsChildren
    docsLangFolders  = $langFolders
    extensionSummary = $extSummary
}
$report | ConvertTo-Json -Depth 6 | Out-File -LiteralPath $jsonPath -Encoding UTF8

Write-Host ""
Write-Host "완료!" -ForegroundColor Green
Write-Host "  텍스트 리포트 : $txtPath" -ForegroundColor Green
Write-Host "  JSON 리포트   : $jsonPath" -ForegroundColor Green
Write-Host ""
Write-Host "이 두 파일을 보내주시면 됩니다." -ForegroundColor Cyan
