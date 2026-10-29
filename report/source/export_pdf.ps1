# Update the table of contents and fields with Microsoft Word, then save the report as PDF in the course folder.
# usage (PowerShell 7): & ".\export_pdf.ps1"
$project = Split-Path -Parent $PSScriptRoot
$course = Split-Path -Parent $project
$docx = Join-Path $project "Deep Learning - Final Project Report.docx"
$pdf = Join-Path $course "Deep Learning - Final Project Report.pdf"
$word = New-Object -ComObject Word.Application
$word.Visible = $false
try {
    $doc = $word.Documents.Open($docx)
    foreach ($toc in $doc.TablesOfContents) { $toc.Update() }
    $doc.Fields.Update() | Out-Null
    $doc.Save()
    $doc.ExportAsFixedFormat($pdf, 17)  # wdExportFormatPDF
    $doc.Close()
} finally {
    $word.Quit()
    [System.Runtime.InteropServices.Marshal]::ReleaseComObject($word) | Out-Null
}
Write-Output "saved $pdf"
