import os
import sqlite3
import google.generativeai as genai
from PIL import Image
import io
import json
import fitz  # PyMuPDF
import uuid
from flask import Flask, request, render_template, redirect, url_for, flash, jsonify, session
from werkzeug.utils import secure_filename
import re

# --- Flask App Configuration ---
app = Flask(__name__)
app.secret_key = os.environ.get('FLASK_SECRET_KEY', 'default_dev_key_change_in_production')
UPLOAD_FOLDER = 'uploads'
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'pdf'}

if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)

app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

# --- Configure Google Generative AI ---
genai.configure(api_key=os.environ.get("GEMINI_API_KEY"))
model = genai.GenerativeModel('gemini-flash-latest')

# Simple in-memory cache for ingredient descriptions to reduce API calls
ingredient_cache = {}

# --- Database Configuration ---
DATABASE_NAME = os.path.join(app.root_path, 'nafdac_regulations.db')

NAFDAC_PROMPT_TEMPLATE = """
You are an expert NAFDAC (National Agency for Food and Drug Administration and Control) compliance officer.
Your task is to review a product label based on the provided label information and NAFDAC Regulations 2021.

**STEP-BY-STEP ANALYSIS REQUIRED:**
1. **Extract Core Data:** Identify the Brand Name, Product Name, Manufacturer Address, and all claims.
2. **Cross-Reference Origin (CRITICAL):** Compare any geographical names in the Brand/Product Name (e.g., "London", "Paris", "Swiss") with the actual Manufacturer Address. If they do not match (e.g., Brand says "London" but address is "Nigeria"), this is a severe violation of Regulation 3(4) - Misleading Origin. You MUST flag this.
3. **Eagle-Eye Checks:** Look for spelling errors (e.g., "Inflamable" instead of "Flammable"), missing symbols (e.g., °C), and contradictory text.
4. **Standard Checks:** Verify presence of Batch No, Expiry Date, Net Content, Ingredients, and NAFDAC Reg No. (Note: Ignore missing Reg No, Dates, or Batch No IF a clear blank placeholder is visible for new products).

Identify specific non-compliance issues and suggest concrete corrections. Your response MUST be a JSON object matching this exact structure:
{{
    "product_name": "Extracted product name.",
    "manufacturer_address_detected": "Extracted address",
    "analysis_reasoning": "Briefly explain your step-by-step analysis here. Explicitly state if the brand name implies a different origin than the actual manufacturer address, and note any spelling errors found.",
    "compliance_status": "Compliant" | "Non-Compliant",
    "issues": [
        {{
            "description": "Detailed description of the issue. DO NOT cite specific regulation numbers here (e.g., do not write 'violates Regulation 3(6)'). The system will automatically attach the correct citation."
        }}
    ],
    "suggested_corrections": ["Correction 1"],
    "ingredients_list": ["Ingredient 1"],
    "key_ingredient_uses": [{{"ingredient": "Name", "uses": "Uses"}}]
}}
"""

def get_relevant_regulations(keywords, product_type_filter='Cosmetics'):
    conn = sqlite3.connect(DATABASE_NAME)
    cursor = conn.cursor()
    
    # Detect schema
    cursor.execute("PRAGMA table_info(regulations)")
    columns = [col[1] for col in cursor.fetchall()]
    is_new_schema = 'requirement' in columns

    if is_new_schema:
        query = "SELECT section, category, requirement, keywords FROM regulations WHERE 1=1"
        params = []
        if keywords:
            keyword_clauses = ["(keywords LIKE ? OR requirement LIKE ? OR section LIKE ?)"]
            params.extend([f'%{keywords}%', f'%{keywords}%', f'%{keywords}%'])
            query += " AND " + " AND ".join(keyword_clauses)
    else:
        query = "SELECT section_number, topic, rule_text, keywords FROM regulations WHERE 1=1"
        params = []
        if product_type_filter:
            type_clauses = [f"product_type LIKE ?"]
            params.append(f'%{product_type_filter}%')
            query += " AND (" + " OR ".join(type_clauses) + ")"
        if keywords:
            keyword_clauses = ["(keywords LIKE ? OR rule_text LIKE ? OR topic LIKE ?)"]
            params.extend([f'%{keywords}%', f'%{keywords}%', f'%{keywords}%'])
            query += " AND " + " AND ".join(keyword_clauses)
    
    query += " LIMIT 10"
    try:
        cursor.execute(query, params)
        regulations = cursor.fetchall()
    except sqlite3.Error:
        return "Error fetching regulations."
    finally:
        conn.close()

    formatted = []
    for reg in regulations:
        if is_new_schema:
            formatted.append(f"{reg[0]} ({reg[1]}):\nFull text: \"{reg[2]}\"")
        else:
            formatted.append(f"Regulation {reg[0]}: {reg[1]}\nFull text: \"{reg[2]}\"")
    return "\n\n".join(formatted) if formatted else "No specific regulations found."

def get_specific_regulation_for_citation(issue_description, product_type_filter='Cosmetics'):
    conn = None
    try:
        conn = sqlite3.connect(DATABASE_NAME)
        cursor = conn.cursor()
        issue_lower = issue_description.lower()
        
        # 1. Robust Keyword/Phrase Priority Mapping
        priority_map = {
            "Regulation 12": ["registration number", "nafdac reg", "reg no", "assigned number", "nafdac number"],
            "Regulation 9(1)": ["expiry date", "date marking", "best before", "exp date", "manufacturing date", "date of manufacture", "mfg date"],
            "Regulation 8": ["batch number", "lot number", "batch no", "lot no", "batch code"],
            "Regulation 5(1)": ["ingredients", "composition", "declaration of ingredients", "list of ingredients", "predominance"],
            "Regulation 7(1)": ["manufacturer name", "location address", "produced by", "packer", "country of origin", "manufacturer address"],
            "Regulation 6(1)": ["net content", "metric system", "average net", "weight", "volume", "quantity", "net weight"],
            "Regulation 10": ["storage conditions", "store in", "keep in", "storage instruction"],
            "Regulation 4(1)": ["product name", "identity", "nature of the product", "brand name", "common name"],
            "Regulation 13": ["directions for use", "how to use", "utilisation", "reconstitution", "usage instructions"],
            "Regulation 14(1)": ["warning", "caution", "safety", "danger", "adequate warning", "precautions"],
            "Regulation 3(12)": ["english", "language", "translated"],
            "Regulation 3(11)": ["claims", "substantiation", "substantiated", "proven"],
            "Regulation 3(4)": ["false", "misleading", "deceptive", "erroneous", "impression"],
            "Regulation 3(2)": ["font size", "legibility", "background", "obscuring", "clarity", "prominent", "readable"],
            "Regulation 3(1)": ["informative", "accurate", "distinct"],
            "Regulation 2(2)": ["inner container", "outer container", "affixed", "wrapper"]
        }

        for section, keywords in priority_map.items():
            if any(kw in issue_lower for kw in keywords):
                return section

        # Detect schema
        cursor.execute("PRAGMA table_info(regulations)")
        columns = [col[1] for col in cursor.fetchall()]
        is_new_schema = 'requirement' in columns

        # 2. Lightweight NLP Scoring (TF/Overlap) for Contextual Matching
        if is_new_schema:
            cursor.execute("SELECT section, category, requirement, keywords FROM regulations")
        else:
            cursor.execute("SELECT section_number, topic, rule_text, keywords FROM regulations WHERE product_type LIKE ?", (f'%{product_type_filter}%',))
            
        all_regs = cursor.fetchall()
        
        if not all_regs and not is_new_schema:
            cursor.execute("SELECT section_number, topic, rule_text, keywords FROM regulations")
            all_regs = cursor.fetchall()

        stop_words = {'the', 'is', 'in', 'and', 'to', 'a', 'of', 'for', 'on', 'with', 'as', 'by', 'an', 'this', 'that', 'product', 'label', 'missing', 'not', 'stated', 'indicated', 'required', 'must', 'be', 'should', 'are', 'or'}
        
        def tokenize(text):
            if not text: return set()
            words = re.findall(r'\b[a-z]{3,}\b', text.lower())
            return set(w for w in words if w not in stop_words)

        issue_tokens = tokenize(issue_description)
        
        best_section = "Regulation 3(6)" # Default fallback
        best_score = 0
        
        for section, topic, rule_text, keywords in all_regs:
            score = 0
            topic_tokens = tokenize(topic)
            rule_tokens = tokenize(rule_text)
            keyword_tokens = tokenize(keywords)
            
            # Calculate overlaps
            topic_overlap = len(issue_tokens.intersection(topic_tokens))
            keyword_overlap = len(issue_tokens.intersection(keyword_tokens))
            rule_overlap = len(issue_tokens.intersection(rule_tokens))
            
            # Weighted score: Keywords and Topics are highly indicative
            score = (keyword_overlap * 4) + (topic_overlap * 3) + (rule_overlap * 1)
            
            # Bonus for exact phrase matches in keywords
            if keywords:
                for kw in keywords.split(','):
                    kw = kw.strip().lower()
                    if kw and kw in issue_lower:
                        score += 10 # Strong signal
                        
            if score > best_score:
                best_score = score
                best_section = section
                
        if best_score > 2:
            return best_section
            
        return "Regulation 3(6)"
    except Exception as e:
        print(f"Citation matching error: {e}")
        return "Regulation 3(6)"
    finally:
        if conn: conn.close()

def make_regulations_clickable(text, color_class):
    pattern = r'(?i)(Regulation\s+\d+(?:\(\w+\))?)'
    replacement = rf'<span class="regulation-link cursor-pointer underline underline-offset-2 font-bold {color_class}" data-section="\1">\1</span>'
    return re.sub(pattern, replacement, text)

def pdf_to_image(pdf_path):
    try:
        doc = fitz.open(pdf_path)
        page = doc.load_page(0)
        pix = page.get_pixmap(matrix=fitz.Matrix(2, 2))
        unique_filename = f"pdf_conv_{uuid.uuid4().hex}.png"
        output_path = os.path.join(app.config['UPLOAD_FOLDER'], unique_filename)
        pix.save(output_path)
        doc.close()
        return output_path
    except:
        return None

def check_compliance(label_image_path):
    try:
        with Image.open(label_image_path) as img:
            img_byte_arr = io.BytesIO()
            img.save(img_byte_arr, format='PNG')
            img_data = img_byte_arr.getvalue()

            image_part = {"mime_type": "image/png", "data": img_data}
            regulations_context = get_relevant_regulations("label, cosmetic", 'Cosmetics')

            prompt_parts = [
                NAFDAC_PROMPT_TEMPLATE.format(label_info="[Image Analysis]", regulations_context=regulations_context),
                image_part
            ]

            response = model.generate_content(prompt_parts)
            ai_data = json.loads(response.text.replace('```json', '').replace('```', '').strip())

            product_name = ai_data.get("product_name", "Unknown")
            final_issues = []
            directive = []

            if ai_data.get("compliance_status") == "Non-Compliant":
                directive.append(f"Analysis of {product_name} reveals non-compliance with NAFDAC Cosmetics Labeling Regulations 2021.")
                for issue in ai_data.get("issues", []):
                    raw_desc = issue.get("description")
                    reg = get_specific_regulation_for_citation(raw_desc)
                    
                    # Sync any AI-cited regulation with the backend's specific regulation to prevent mismatch
                    desc_synced = re.sub(r'(?i)Regulation\s+\d+(?:\(\w+\))?', reg, raw_desc)
                    
                    # Make clickable for issue card
                    desc_html = make_regulations_clickable(desc_synced, "text-rose-700 hover:text-rose-900 decoration-rose-400/50")
                    final_issues.append({
                        "description": desc_html, 
                        "raw_desc": desc_synced, 
                        "regulation_cited": reg
                    })
                    
                    # Build directive text
                    directive_text = desc_synced
                    if reg.lower() not in desc_synced.lower():
                        directive_text += f" ({reg})"
                        
                    # Make clickable for directive
                    directive_html = make_regulations_clickable(directive_text, "text-emerald-300 hover:text-emerald-100 decoration-emerald-400/50")
                    directive.append(f" - {directive_html}")
            else:
                directive.append(f"The label for {product_name} appears compliant with NAFDAC 2021 regulations.")

            return {
                "product_name": product_name,
                "compliance_status": ai_data.get("compliance_status"),
                "issues": final_issues,
                "suggested_corrections": ai_data.get("suggested_corrections", []),
                "ingredients_list": ai_data.get("ingredients_list", []),
                "key_ingredient_uses": ai_data.get("key_ingredient_uses", []),
                "compliance_directive_formatted": directive
            }
    except Exception as e:
        return {"error": str(e)}

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/upload_file', methods=['POST'])
def upload_file():
    file = request.files.get('file')
    if file and file.filename:
        filename = secure_filename(file.filename)
        path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        file.save(path)
        
        analysis_path = path
        temp_path = None
        if filename.lower().endswith('.pdf'):
            temp_path = pdf_to_image(path)
            analysis_path = temp_path
        
        results = check_compliance(analysis_path)
        session['latest_results'] = results
        
        if os.path.exists(path): os.remove(path)
        if temp_path and os.path.exists(temp_path): os.remove(temp_path)
        
        return render_template('results.html', results=results)
    return redirect(url_for('index'))

@app.route('/get_regulation/<path:section_number>')
def get_regulation(section_number):
    try:
        conn = sqlite3.connect(DATABASE_NAME)
        cursor = conn.cursor()
        
        clean_section = section_number.replace('Regulation', '').strip()
        like_pattern = f'%{clean_section}%' if clean_section else section_number
        
        # Try primary schema (rule_text, topic, section_number)
        try:
            cursor.execute("SELECT rule_text, topic FROM regulations WHERE section_number = ? OR section_number LIKE ? LIMIT 1", 
                           (section_number, like_pattern))
            res = cursor.fetchone()
            if res:
                topic = res[1] if res[1] else f"Regulation {clean_section}"
                conn.close()
                return jsonify({"success": True, "section_number": section_number, "topic": topic, "rule_text": res[0]})
        except sqlite3.OperationalError:
            pass # Column might not exist, try alternative schema
            
        # Try alternative schema (requirement, category, section) based on user's JSON
        try:
            cursor.execute("SELECT requirement, category FROM regulations WHERE section = ? OR section LIKE ? LIMIT 1", 
                           (section_number, like_pattern))
            res = cursor.fetchone()
            if res:
                topic = res[1].capitalize() if res[1] else f"Regulation {clean_section}"
                conn.close()
                return jsonify({"success": True, "section_number": section_number, "topic": topic, "rule_text": res[0]})
        except sqlite3.OperationalError:
            pass
            
        conn.close()
        return jsonify({"success": False}), 404
        
    except Exception as e:
        print(f"Error fetching regulation: {e}")
        return jsonify({"success": False, "error": str(e)}), 500

@app.route('/view_history', methods=['POST'])
def view_history():
    history_data_json = request.form.get('history_data')
    if history_data_json:
        try:
            history_data = json.loads(history_data_json)
            session['latest_results'] = history_data
            return render_template('results.html', results=history_data)
        except json.JSONDecodeError:
            pass
    return redirect(url_for('index'))

@app.route('/download_report', methods=['GET', 'POST'])
def download_report():
    results = session.get('latest_results')
    if not results:
        return redirect(url_for('index'))
        
    if request.method == 'POST':
        modified_issues_json = request.form.get('modified_issues')
        if modified_issues_json:
            try:
                modified_issues = json.loads(modified_issues_json)
                
                # Rebuild the issues list with proper HTML formatting for the description
                formatted_issues = []
                for issue in modified_issues:
                    raw_desc = issue.get('raw_desc', '')
                    reg = issue.get('regulation_cited', '')
                    
                    # Make clickable for issue card (if they view it again)
                    desc_html = make_regulations_clickable(raw_desc, "text-rose-700 hover:text-rose-900 decoration-rose-400/50")
                    
                    formatted_issues.append({
                        "description": desc_html,
                        "raw_desc": raw_desc,
                        "regulation_cited": reg
                    })
                    
                results['issues'] = formatted_issues
                
                # Re-evaluate compliance based on modified issues
                if len(formatted_issues) == 0:
                    results['compliance_status'] = 'Compliant'
                    results['compliance_directive_formatted'] = [f"The label for {results.get('product_name')} appears compliant with NAFDAC 2021 regulations."]
                else:
                    results['compliance_status'] = 'Non-Compliant'
                    directive = [f"Analysis of {results.get('product_name')} reveals non-compliance with NAFDAC Cosmetics Labeling Regulations 2021."]
                    for issue in formatted_issues:
                        directive_text = issue['raw_desc']
                        reg = issue['regulation_cited']
                        if reg.lower() not in directive_text.lower():
                            directive_text += f" ({reg})"
                        directive_html = make_regulations_clickable(directive_text, "text-emerald-300 hover:text-emerald-100 decoration-emerald-400/50")
                        directive.append(f" - {directive_html}")
                    results['compliance_directive_formatted'] = directive
                    
                session['latest_results'] = results
            except json.JSONDecodeError:
                pass
                
    return render_template('report.html', results=results)

@app.route('/api/ingredient-info', methods=['POST'])
def ingredient_info():
    data = request.get_json()
    ingredient = data.get('ingredient')
    if not ingredient:
        return jsonify({"error": "No ingredient provided"}), 400
    
    ingredient_lower = ingredient.lower().strip()
    
    # Check cache first to save API quota
    if ingredient_lower in ingredient_cache:
        return jsonify({"description": ingredient_cache[ingredient_lower]})
    
    prompt = f"Briefly explain what the ingredient '{ingredient}' does in cosmetics or food products in 1-2 short sentences. Keep it concise."
    try:
        response = model.generate_content(prompt)
        description = response.text.strip()
        
        # Save to cache
        ingredient_cache[ingredient_lower] = description
        
        return jsonify({"description": description})
    except Exception as e:
        error_msg = str(e)
        if "429" in error_msg or "Quota exceeded" in error_msg:
            return jsonify({"error": "Rate limit exceeded. Please wait a few seconds and try again."}), 429
        return jsonify({"error": error_msg}), 500

@app.route('/sw.js')
def sw():
    return app.send_static_file('sw.js')

if __name__ == '__main__':
    app.run(port=3000)
