$ErrorActionPreference = 'Stop'
$examCodes = @('111020','111100','112020','112100','113020','113090','114020','114090','115020','115090')
$allRows = [System.Collections.Generic.List[object]]::new()
foreach ($examCode in $examCodes) {
 $year = [int]$examCode.Substring(0,3)
 $sitting = if ($examCode.EndsWith('020')) { 1 } else { 2 }
 $folder = "study_radiographer/sources/${year}_${sitting}"
 New-Item -ItemType Directory -Path $folder -Force | Out-Null
 $pageUrl = "https://wwwq.moex.gov.tw/exam/wFrmExamQandASearch.aspx?e=$examCode&y=$($year+1911)"
 $page = Invoke-WebRequest -Uri $pageUrl -TimeoutSec 60
 $page.Content | Set-Content -LiteralPath "$folder/source_page.html" -Encoding utf8
 $links = $page.Links | Where-Object { $_.href -match 'c=309(?:&|$)' } | Select-Object -ExpandProperty href -Unique
 if (!$links) { throw "No radiographer links: $examCode" }
 $qCount = 0
 foreach ($link in $links) {
  $decoded = [System.Net.WebUtility]::HtmlDecode($link)
  $subject = [regex]::Match($decoded,'(?:\?|&)s=(\d+)').Groups[1].Value
  $kind = [regex]::Match($decoded,'(?:\?|&)t=(\w+)').Groups[1].Value
  if ($kind -notin @('Q','S','M')) { continue }
  if ($kind -eq 'Q') { $qCount++ }
  $url = [Uri]::new([Uri]$pageUrl,$decoded).AbsoluteUri
  $path = "$folder/${subject}_${kind}.pdf"
  if (!(Test-Path -LiteralPath $path)) {
   for ($attempt=1; $attempt -le 3; $attempt++) {
    try { Invoke-WebRequest -Uri $url -OutFile $path -TimeoutSec 60; break }
    catch { if ($attempt -eq 3) { throw } }
   }
  }
  $bytes = [IO.File]::ReadAllBytes((Resolve-Path -LiteralPath $path))
  if ($bytes.Length -lt 5 -or [Text.Encoding]::ASCII.GetString($bytes,0,5) -ne '%PDF-') { throw "Not PDF: $path" }
  $allRows.Add([pscustomobject]@{exam=$examCode;year=$year;sitting=$sitting;subject=$subject;type=$kind;url=$url;path=$path;bytes=$bytes.Length;sha256=(Get-FileHash -LiteralPath $path -Algorithm SHA256).Hash;retrieved='2026-09-09';source_page=$pageUrl})
 }
 if ($qCount -ne 6) { throw "Expected 6 papers: $examCode has $qCount" }
 $allRows | Export-Csv -LiteralPath 'study_radiographer/sources/manifest_5years.csv' -Encoding utf8 -NoTypeInformation
 Write-Output "$examCode completed: $qCount papers, $($links.Count) files"
}
Write-Output "TOTAL $($allRows.Count) PDF files"
