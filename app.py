from flask import Flask, request, jsonify
from flask_cors import CORS
import os
from dotenv import load_dotenv
import gspread
from google.oauth2.service_account import Credentials
import pandas as pd
import json
from datetime import datetime
from matching_system import MatchingSystem
from candidate_registration import CandidateRegistrationSystem

# Load environment variables
load_dotenv()

# Initialize Flask app
app = Flask(__name__)
CORS(app)

# Google Sheets setup
scope = ['https://spreadsheets.google.com/feeds',
         'https://www.googleapis.com/auth/drive']

# Load credentials from file
creds = Credentials.from_service_account_file(
    os.getenv('GOOGLE_CREDENTIALS_PATH'),
    scopes=scope
)

# Authorize the client
client = gspread.authorize(creds)

# Open the sheets
candidates_sheet = client.open_by_key(os.getenv('CANDIDATES_SHEET_ID'))
employers_sheet = client.open_by_key(os.getenv('EMPLOYERS_SHEET_ID'))
companies_sheet = client.open_by_key(os.getenv('COMPANIES_SHEET_ID'))

# Initialize matching system
matching_system = MatchingSystem()

# Initialize registration system
registration_system = CandidateRegistrationSystem(
    credentials_path=os.getenv('GOOGLE_CREDENTIALS_PATH'),
    users_sheet_id=os.getenv('USERS_SHEET_ID')  # Add this to .env after first run
)

@app.route('/health', methods=['GET'])
def health_check():
    """Health check endpoint"""
    return jsonify({
        'status': 'healthy',
        'service': 'AI Recruitment Platform API',
        'timestamp': datetime.now().isoformat()
    })

@app.route('/test_sheets', methods=['GET'])
def test_sheets():
    """Test Google Sheets connection"""
    try:
        # Get data from sheets
        candidates_data = candidates_sheet.sheet1.get_all_records()
        employers_data = employers_sheet.sheet1.get_all_records()
        companies_data = companies_sheet.sheet1.get_all_records()
        
        return jsonify({
            'success': True,
            'candidates_count': len(candidates_data),
            'employers_count': len(employers_data),
            'companies_count': len(companies_data),
            'sample_candidate': candidates_data[0] if candidates_data else None,
            'sample_job': employers_data[0] if employers_data else None,
            'sample_company': companies_data[0] if companies_data else None
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/get_jobs', methods=['GET'])
def get_jobs():
    """Get all job listings"""
    try:
        jobs_data = employers_sheet.sheet1.get_all_records()
        return jsonify({
            'success': True,
            'jobs': jobs_data,
            'count': len(jobs_data)
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/find_matches', methods=['POST'])
def find_matches():
    """Find matching candidates for a job"""
    try:
        job_data = request.json
        
        # Get all candidates
        candidates_data = candidates_sheet.sheet1.get_all_records()
        
        # Convert to DataFrames
        candidates_df = pd.DataFrame(candidates_data)
        
        # Find matches using the matching system
        matches = matching_system.find_matches(job_data, candidates_df)
        
        return jsonify({
            'success': True,
            'job_title': job_data.get('job_title', 'Unknown'),
            'company': job_data.get('company_name', 'Unknown'),
            'matches': matches,
            'total_candidates_analyzed': len(candidates_df)
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/get_candidate/<candidate_id>', methods=['GET'])
def get_candidate(candidate_id):
    """Get candidate details by ID"""
    try:
        candidates_data = candidates_sheet.sheet1.get_all_records()
        
        for candidate in candidates_data:
            if str(candidate.get('candidate_id')) == str(candidate_id):
                return jsonify({
                    'success': True,
                    'candidate': candidate
                })
        
        return jsonify({
            'success': False,
            'error': 'Candidate not found'
        }), 404
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/get_candidates', methods=['GET'])
def get_candidates():
    """Get all candidates"""
    try:
        candidates_data = candidates_sheet.sheet1.get_all_records()
        return jsonify({
            'success': True,
            'candidates': candidates_data,
            'count': len(candidates_data)
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/add_candidate', methods=['POST'])
def add_candidate():
    """Add a new candidate to Google Sheets"""
    try:
        candidate_data = request.json
        
        # Generate candidate ID
        candidate_id = f"CAN_{datetime.now().strftime('%Y%m%d%H%M%S')}"
        
        # Prepare row data
        row_data = [
            candidate_id,
            candidate_data.get('full_name', ''),
            candidate_data.get('email', ''),
            candidate_data.get('phone', ''),
            candidate_data.get('location', ''),
            candidate_data.get('current_position', ''),
            candidate_data.get('years_experience', ''),
            candidate_data.get('skills', ''),
            candidate_data.get('education', ''),
            candidate_data.get('languages', ''),
            candidate_data.get('portfolio_url', ''),
            candidate_data.get('linkedin_url', ''),
            candidate_data.get('github_url', ''),
            candidate_data.get('expected_salary', ''),
            candidate_data.get('notice_period', ''),
            candidate_data.get('work_authorization', ''),
            candidate_data.get('willing_to_relocate', ''),
            candidate_data.get('preferred_locations', ''),
            candidate_data.get('achievements', ''),
            candidate_data.get('profile_summary', ''),
            datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            'active'
        ]
        
        # Append to sheet
        candidates_sheet.sheet1.append_row(row_data)
        
        return jsonify({
            'success': True,
            'candidate_id': candidate_id,
            'message': 'Candidate added successfully'
        }), 201
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/add_job', methods=['POST'])
def add_job():
    """Add a new job posting to Google Sheets"""
    try:
        job_data = request.json
        
        # Generate job ID
        job_id = f"JOB_{datetime.now().strftime('%Y%m%d%H%M%S')}"
        
        # Prepare row data
        row_data = [
            job_id,
            job_data.get('company_name', ''),
            job_data.get('job_title', ''),
            job_data.get('department', ''),
            job_data.get('location', ''),
            job_data.get('employment_type', ''),
            job_data.get('experience_required', ''),
            job_data.get('salary_range', ''),
            job_data.get('job_description', ''),
            job_data.get('required_skills', ''),
            job_data.get('preferred_skills', ''),
            job_data.get('education_requirement', ''),
            job_data.get('benefits', ''),
            job_data.get('application_deadline', ''),
            job_data.get('contact_email', ''),
            job_data.get('contact_phone', ''),
            job_data.get('company_website', ''),
            job_data.get('remote_work_option', ''),
            job_data.get('visa_sponsorship', ''),
            datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            'active'
        ]
        
        # Append to sheet
        employers_sheet.sheet1.append_row(row_data)
        
        return jsonify({
            'success': True,
            'job_id': job_id,
            'message': 'Job posted successfully'
        }), 201
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

# ===== NEW REGISTRATION ENDPOINTS =====

@app.route('/register', methods=['POST'])
def register_candidate():
    """Register a new candidate with encrypted credentials"""
    try:
        data = request.json
        username = data.get('username')
        email = data.get('email')
        password = data.get('password')
        
        if not all([username, email, password]):
            return jsonify({
                'success': False,
                'error': 'Username, email, and password are required.'
            }), 400
        
        result = registration_system.register_candidate(username, email, password)
        
        if result['success']:
            # Store the users sheet ID in environment for future use
            if 'sheet_id' in result:
                print(f"IMPORTANT: Add this to your .env file: USERS_SHEET_ID={result['sheet_id']}")
            return jsonify(result), 201
        else:
            return jsonify(result), 400
            
    except Exception as e:
        return jsonify({
            'success': False,
            'error': f'Server error: {str(e)}'
        }), 500

@app.route('/login', methods=['POST'])
def login_candidate():
    """Login a candidate"""
    try:
        data = request.json
        username = data.get('username')
        password = data.get('password')
        
        if not all([username, password]):
            return jsonify({
                'success': False,
                'error': 'Username and password are required.'
            }), 400
        
        result = registration_system.login_candidate(username, password)
        
        if result['success']:
            # In production, you'd create a session or JWT token here
            # For now, we'll just return the user data
            return jsonify(result), 200
        else:
            return jsonify(result), 401
            
    except Exception as e:
        return jsonify({
            'success': False,
            'error': f'Server error: {str(e)}'
        }), 500

@app.route('/user/<user_id>', methods=['GET'])
def get_user(user_id):
    """Get user details by ID"""
    try:
        result = registration_system.get_user_by_id(user_id)
        
        if result['success']:
            return jsonify(result), 200
        else:
            return jsonify(result), 404
            
    except Exception as e:
        return jsonify({
            'success': False,
            'error': f'Server error: {str(e)}'
        }), 500

@app.route('/link_profile', methods=['POST'])
def link_profile():
    """Link a user account to a candidate profile"""
    try:
        data = request.json
        user_id = data.get('user_id')
        candidate_id = data.get('candidate_id')
        
        if not all([user_id, candidate_id]):
            return jsonify({
                'success': False,
                'error': 'User ID and Candidate ID are required.'
            }), 400
        
        # Update the users sheet to link the candidate profile
        if hasattr(registration_system, 'users_sheet'):
            worksheet = registration_system.users_sheet.sheet1
            all_values = worksheet.get_all_values()
            
            for i, row in enumerate(all_values[1:], start=2):
                if row[0] == user_id:
                    # Update candidate_profile_id column (index 8)
                    worksheet.update_cell(i, 9, candidate_id)
                    return jsonify({
                        'success': True,
                        'message': 'Profile linked successfully'
                    }), 200
            
            return jsonify({
                'success': False,
                'error': 'User not found'
            }), 404
        else:
            return jsonify({
                'success': False,
                'error': 'Users sheet not initialized'
            }), 500
            
    except Exception as e:
        return jsonify({
            'success': False,
            'error': f'Server error: {str(e)}'
        }), 500

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=False)
