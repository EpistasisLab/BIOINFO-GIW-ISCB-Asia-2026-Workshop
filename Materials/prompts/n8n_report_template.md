<style>
body { font-family: -apple-system, "Segoe UI", Arial, sans-serif; max-width: 960px; margin: 40px auto; padding: 0 16px; line-height: 1.55; color: #1f2933; }
h1 { border-bottom: 3px solid #1f6feb; padding-bottom: 6px; }
h2 { margin-top: 2em; border-bottom: 1px solid #d0d7de; padding-bottom: 4px; color: #0b3d91; }
h3, h4 { color: #0b3d91; }
code { font-family: Menlo, Consolas, monospace; font-weight: bold; font-size: 0.88em; background: #eef2f7; padding: 1px 5px; border-radius: 4px; }
table { border-collapse: collapse; width: 100%; margin: 1em 0; font-size: 0.9em; }
th { background: #0b3d91; color: #ffffff; text-align: left; }
th, td { border: 1px solid #d0d7de; padding: 6px 10px; vertical-align: top; }
tr:nth-child(even) td { background: #f6f8fa; }
a { color: #1f6feb; }
hr { border: none; border-top: 1px solid #d0d7de; margin: 2em 0; }
@media print { body { margin: 0; max-width: none; } tr { page-break-inside: avoid; } th, tr:nth-child(even) td { -webkit-print-color-adjust: exact; print-color-adjust: exact; } }
</style>

# Heart failure after MI: literature and data report

- **Question:** {{ $('When chat message received').first().json.chatInput }}
- **Date:** {{ $now.toFormat('yyyy-MM-dd') }}

## Part 1. What the literature says (Literature Scout)

{{ $('Literature Scout').first().json.output }}

## Part 2. What our data can support (Data Analyst)

{{ $json.output }}