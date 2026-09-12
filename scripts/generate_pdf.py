import os
import shutil
import subprocess
import html
import docx

def build_html_from_docx(docx_path):
    doc = docx.Document(docx_path)
    
    html_parts = []
    html_parts.append("""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<title>Idea Diligence Agent - Project Specification</title>
<style>
  @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800&family=JetBrains+Mono:wght@400;500;600&display=swap');

  @page {
    size: A4;
    margin: 18mm 16mm;
    @bottom-center {
      content: counter(page);
    }
  }

  * {
    box-sizing: border-box;
  }

  body {
    font-family: 'Inter', -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
    color: #1e293b;
    line-height: 1.6;
    font-size: 10.5pt;
    margin: 0;
    padding: 24px;
    background-color: #ffffff;
  }

  .header-card {
    background: linear-gradient(135deg, #0f172a 0%, #1e1b4b 100%);
    color: #ffffff;
    padding: 28px;
    border-radius: 12px;
    margin-bottom: 28px;
    box-shadow: 0 4px 15px rgba(0, 0, 0, 0.08);
  }

  .header-card h1 {
    font-size: 24pt;
    font-weight: 800;
    margin: 0 0 8px 0;
    letter-spacing: -0.5px;
    color: #f8fafc;
  }

  .header-card .tagline {
    font-size: 11pt;
    color: #cbd5e1;
    margin-bottom: 16px;
    line-height: 1.5;
  }

  .badges {
    display: flex;
    gap: 10px;
    flex-wrap: wrap;
  }

  .badge {
    display: inline-block;
    padding: 4px 10px;
    border-radius: 6px;
    font-size: 8.5pt;
    font-weight: 600;
    letter-spacing: 0.3px;
    text-transform: uppercase;
  }

  .badge-primary { background: #3b82f6; color: #ffffff; }
  .badge-secondary { background: #6366f1; color: #ffffff; }
  .badge-dark { background: rgba(255, 255, 255, 0.15); color: #f8fafc; border: 1px solid rgba(255, 255, 255, 0.2); }

  .section-divider {
    border: none;
    border-top: 2px solid #e2e8f0;
    margin: 32px 0 24px 0;
  }

  .section-badge-header {
    background: #f1f5f9;
    border-left: 5px solid #2563eb;
    padding: 12px 18px;
    border-radius: 0 8px 8px 0;
    margin: 28px 0 16px 0;
  }

  .section-badge-header.gokul {
    border-left-color: #7c3aed;
    background: #f5f3ff;
  }

  .section-badge-header h2 {
    margin: 0;
    font-size: 16pt;
    color: #0f172a;
    font-weight: 700;
  }

  .section-badge-header.gokul h2 {
    color: #4c1d95;
  }

  h1 { font-size: 18pt; font-weight: 700; color: #0f172a; margin-top: 22px; margin-bottom: 8px; }
  h2 { font-size: 13pt; font-weight: 700; color: #1e293b; margin-top: 18px; margin-bottom: 6px; }
  h3 { font-size: 11pt; font-weight: 600; color: #334155; margin-top: 14px; margin-bottom: 4px; }

  p {
    margin: 0 0 8px 0;
    color: #334155;
  }

  ul {
    margin: 4px 0 12px 0;
    padding-left: 20px;
  }

  li {
    margin-bottom: 5px;
    color: #334155;
  }

  strong {
    color: #0f172a;
    font-weight: 600;
  }

  .diagram-box {
    background: #0f172a;
    color: #38bdf8;
    font-family: 'JetBrains Mono', monospace;
    font-size: 8.5pt;
    line-height: 1.35;
    padding: 16px;
    border-radius: 8px;
    margin: 14px 0;
    white-space: pre;
    overflow-x: auto;
    box-shadow: inset 0 2px 4px rgba(0,0,0,0.4);
    page-break-inside: avoid;
  }

  .code-block {
    background: #f8fafc;
    color: #0f172a;
    border: 1px solid #e2e8f0;
    font-family: 'JetBrains Mono', monospace;
    font-size: 8.5pt;
    line-height: 1.4;
    padding: 14px;
    border-radius: 6px;
    margin: 12px 0;
    white-space: pre;
    page-break-inside: avoid;
  }

  .callout {
    background: #eff6ff;
    border-left: 4px solid #3b82f6;
    padding: 12px 16px;
    border-radius: 0 6px 6px 0;
    margin: 14px 0;
    font-size: 10pt;
  }

  .callout.tip {
    background: #ecfdf5;
    border-left-color: #10b981;
  }

  .page-break {
    page-break-before: always;
  }
</style>
</head>
<body>

<div class="header-card">
  <div class="badges">
    <span class="badge badge-primary">AWS Strands Agents Hackathon</span>
    <span class="badge badge-secondary">Track: Professional Agents</span>
    <span class="badge badge-dark">Team: Edmund &amp; Gokul</span>
  </div>
  <h1 style="margin-top: 14px;">Idea Diligence Agent</h1>
  <div class="tagline">
    An autonomous AI diligence agent that researches product ideas, competitors, pricing, markets, and revenue models in the background, challenges assumptions, and delivers evidence-backed <strong>GO</strong>, <strong>MODIFY</strong>, or <strong>KILL</strong> decisions.
  </div>
</div>
""")

    current_mode = "intro" # intro, edmund, gokul
    in_ascii_block = False
    ascii_lines = []

    def flush_ascii():
        nonlocal in_ascii_block, ascii_lines
        if ascii_lines:
            text = "\n".join(ascii_lines)
            html_parts.append(f'<div class="diagram-box">{html.escape(text)}</div>\n')
            ascii_lines = []
            in_ascii_block = False

    is_first_edmund = True
    is_first_gokul = True

    for p in doc.paragraphs:
        txt = p.text.rstrip()
        
        # Check if this line is part of ASCII diagram or code block
        is_diagram_line = any(char in txt for char in ['│', '─', '┌', '┐', '└', '┘', '├', '┤', '▼', '▲', '◄', '►', '↙', '↘'])
        is_tree_line = any(char in txt for char in ['├──', '└──', '│']) and not is_diagram_line

        if is_diagram_line:
            ascii_lines.append(txt)
            in_ascii_block = True
            continue
        elif in_ascii_block:
            # Check if this could be an empty line inside a diagram
            if not txt or all(c in ' \t' for c in txt):
                ascii_lines.append(txt)
                continue
            else:
                flush_ascii()

        # Handle headings / mode switches
        if "Edmund's points" in txt:
            flush_ascii()
            current_mode = "edmund"
            html_parts.append("""
<div class="section-badge-header">
  <h2>Edmund's Points: Refined Project Specification &amp; Development Blueprint</h2>
</div>
""")
            continue
        elif "Gokul's Points" in txt:
            flush_ascii()
            current_mode = "gokul"
            html_parts.append("""
<div class="section-divider"></div>
<div class="section-badge-header gokul page-break">
  <h2>Gokul's Points: Architectural Review &amp; Strands SDK Evaluation</h2>
</div>
""")
            continue

        if not txt:
            continue

        # Check styles
        style_name = p.style.name if p.style else ""

        if style_name == "Heading 1" or (txt.startswith(("1.", "2.", "3.", "4.", "5.", "6.", "7.")) and len(txt) < 80):
            html_parts.append(f'<h1>{html.escape(txt)}</h1>\n')
        elif style_name == "Heading 2" or txt.startswith(("Component A:", "Component B:", "Component C:", "Component D:", "Evidence Classification")):
            html_parts.append(f'<h2>{html.escape(txt)}</h2>\n')
        elif style_name == "Heading 3":
            html_parts.append(f'<h3>{html.escape(txt)}</h3>\n')
        elif txt.startswith("• "):
            content = txt[2:].strip()
            # If there's bold prefix
            if ":" in content and len(content.split(":")[0]) < 35:
                prefix, rest = content.split(":", 1)
                html_parts.append(f'<ul><li><strong>{html.escape(prefix)}:</strong>{html.escape(rest)}</li></ul>\n')
            else:
                html_parts.append(f'<ul><li>{html.escape(content)}</li></ul>\n')
        elif txt.startswith("class DiligenceState:") or txt.startswith("ResearchSession"):
            html_parts.append(f'<div class="code-block">{html.escape(txt)}</div>\n')
        elif txt.startswith("----------------------------------------------------------------------"):
            html_parts.append('<div class="section-divider"></div>\n')
        else:
            # Regular paragraph
            if txt.startswith("Below is Edmund's refined"):
                html_parts.append(f'<div class="callout">{html.escape(txt)}</div>\n')
            elif txt.startswith("Yes. Your hypothesis is architecturally sound"):
                html_parts.append(f'<div class="callout tip"><strong>Architectural Assessment:</strong> {html.escape(txt)}</div>\n')
            else:
                html_parts.append(f'<p>{html.escape(txt)}</p>\n')

    flush_ascii()

    html_parts.append("""
</body>
</html>
""")
    return "".join(html_parts)

def main():
    docx_path = "Idea Diligence Agent - Project.docx"
    html_path = os.path.expandvars(r"%TEMP%\project_spec.html")
    pdf_temp_path = os.path.expandvars(r"%TEMP%\Idea_Diligence_Agent_Project.pdf")
    final_pdf = "Idea Diligence Agent - Project.pdf"
    alt_pdf = "Idea Diligence Agent - Project.docx.pdf"

    print("Generating HTML representation from docx...")
    html_content = build_html_from_docx(docx_path)
    with open(html_path, "w", encoding="utf-8") as f:
        f.write(html_content)
    print(f"Wrote HTML to {html_path} ({len(html_content)} bytes)")

    edge_path = r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe"
    if not os.path.exists(edge_path):
        edge_path = r"C:\Program Files\Microsoft\Edge\Application\msedge.exe"
    if not os.path.exists(edge_path):
        edge_path = shutil.which("msedge")

    if not edge_path or not os.path.exists(edge_path):
        raise FileNotFoundError("Microsoft Edge executable not found for PDF conversion")

    print(f"Running Edge headless to render PDF from {html_path}...")
    if os.path.exists(pdf_temp_path):
        os.remove(pdf_temp_path)

    cmd = [
        edge_path,
        "--headless",
        "--disable-gpu",
        "--no-pdf-header-footer",
        f"--print-to-pdf={pdf_temp_path}",
        html_path
    ]
    res = subprocess.run(cmd, capture_output=True, text=True)
    print("Edge process returncode:", res.returncode)

    if not os.path.exists(pdf_temp_path):
        raise RuntimeError(f"Edge did not produce {pdf_temp_path}. Stderr: {res.stderr}")

    shutil.copyfile(pdf_temp_path, final_pdf)
    shutil.copyfile(pdf_temp_path, alt_pdf)

    print(f"Successfully generated {final_pdf} ({os.path.getsize(final_pdf)} bytes)")
    print(f"Successfully copied to {alt_pdf} ({os.path.getsize(alt_pdf)} bytes)")

if __name__ == "__main__":
    main()
