import markdown
import os

def render_markdown_report(report_path):
    """
    Reads a Markdown file, converts it to HTML with custom styling,
    and returns the final HTML string for display.
    """
    if not os.path.exists(report_path):
        return "<div class='text-red-500 italic p-4'>⚠️ Report file could not be found.</div>"

    try:
        with open(report_path, "r", encoding="utf-8") as f:
            md_text = f.read()

        # Convert Markdown -> HTML (Enable 'tables' extension for the metrics section)
        html_body = markdown.markdown(md_text, extensions=['tables', 'fenced_code'])

        # Custom CSS to make the raw HTML look professional
        custom_css = """
        <style>
            .md-report h1 { font-size: 1.5em; font-weight: bold; margin-bottom: 0.5em; color: #1e293b; border-bottom: 2px solid #e2e8f0; padding-bottom: 0.3em; margin-top: 0.5em; }
            .md-report h2 { font-size: 1.25em; font-weight: bold; margin-top: 1.5em; margin-bottom: 0.8em; color: #334155; border-left: 4px solid #3b82f6; padding-left: 0.5em; }
            .md-report h3 { font-size: 1.1em; font-weight: bold; margin-top: 1.2em; margin-bottom: 0.5em; color: #475569; }
            .md-report ul { list-style-type: disc; padding-left: 1.5em; margin-bottom: 1em; }
            .md-report li { margin-bottom: 0.25em; }
            .md-report table { border-collapse: collapse; width: 100%; margin-bottom: 1.5em; font-size: 0.9em; }
            .md-report th { background-color: #f8fafc; text-align: left; padding: 10px; border: 1px solid #e2e8f0; font-weight: bold; color: #475569; }
            .md-report td { padding: 8px; border: 1px solid #e2e8f0; }
            .md-report code { background-color: #f1f5f9; padding: 2px 5px; border-radius: 4px; font-family: monospace; font-size: 0.9em; color: #dc2626; }
            .md-report blockquote { border-left: 4px solid #10b981; padding-left: 1em; color: #065f46; font-style: italic; background-color: #ecfdf5; padding: 0.8em; border-radius: 4px; margin-bottom: 1em; }
        </style>
        """

        # Return combined string
        return f"{custom_css}<div class='md-report'>{html_body}</div>"

    except Exception as e:
        return f"<div class='text-red-500 font-bold p-4'>Error rendering report: {str(e)}</div>"