<#
Convert a PowerPoint (.pptx) file to PDF using PowerPoint COM automation.

Usage (PowerShell):
  .\pptx_to_pdf.ps1 -InputPath .\Deck.pptx -OutputPath .\Deck.pdf

Notes:
- Requires Microsoft PowerPoint installed on Windows.
- If PowerPoint is not available, use LibreOffice in headless mode as an alternative (instructions in README).
#>

param(
    [Parameter(Mandatory=$true)]
    [string] $InputPath,
    [Parameter(Mandatory=$true)]
    [string] $OutputPath
)

if (-not (Test-Path $InputPath)) {
    Write-Error "Input file not found: $InputPath"
    exit 2
}

try {
    $pp = New-Object -ComObject PowerPoint.Application
} catch {
    Write-Error "Failed to create PowerPoint COM object. Is PowerPoint installed?"
    exit 3
}

try {
    # Visible expects a MsoTriState numeric; -1 corresponds to msoTrue
    $pp.Visible = -1
        # Resolve absolute paths
        $inFull = (Get-Item $InputPath).FullName
        $outFull = [System.IO.Path]::GetFullPath($OutputPath)
        $outDir = Split-Path $outFull -Parent
        if (-not (Test-Path $outDir)) {
            New-Item -ItemType Directory -Path $outDir | Out-Null
        }
        $presentation = $pp.Presentations.Open($inFull, $false, $false, $true)
        # Use SaveAs with numeric PDF filetype (32) to avoid enum conversion issues
        $presentation.SaveAs($outFull, 32)
    $presentation.Close()
    Write-Host "Wrote $OutputPath"
} catch {
    Write-Error "Error exporting to PDF: $_"
    exit 4
} finally {
    $pp.Quit()
}
