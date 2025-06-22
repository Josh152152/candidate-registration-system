import pandas as pd
import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
from sentence_transformers import SentenceTransformer
import spacy
import re
from geopy.distance import geodesic
from geopy.geocoders import Nominatim
from datetime import datetime

class MatchingSystem:
    def __init__(self):
        """Initialize the AI matching system with NLP models"""
        # Load spaCy model for NLP
        try:
            self.nlp = spacy.load("en_core_web_sm")
        except:
            print("Installing spaCy model...")
            os.system("python -m spacy download en_core_web_sm")
            self.nlp = spacy.load("en_core_web_sm")
        
        # Initialize sentence transformer for semantic matching
        self.sentence_model = SentenceTransformer('all-MiniLM-L6-v2')
        
        # Initialize geocoder for location matching
        self.geolocator = Nominatim(user_agent="ai_recruitment_platform")
        
        # Skills database (can be expanded)
        self.tech_skills = {
            'programming': ['python', 'java', 'javascript', 'c++', 'c#', 'ruby', 'go', 'rust', 'swift', 'kotlin', 'php', 'typescript', 'scala', 'r', 'matlab'],
            'web': ['html', 'css', 'react', 'angular', 'vue', 'node.js', 'django', 'flask', 'spring', 'express', 'next.js', 'nuxt.js'],
            'database': ['sql', 'mysql', 'postgresql', 'mongodb', 'redis', 'cassandra', 'elasticsearch', 'dynamodb'],
            'cloud': ['aws', 'azure', 'gcp', 'docker', 'kubernetes', 'terraform', 'jenkins', 'ci/cd'],
            'data': ['pandas', 'numpy', 'scikit-learn', 'tensorflow', 'pytorch', 'keras', 'tableau', 'power bi', 'spark'],
            'mobile': ['android', 'ios', 'react native', 'flutter', 'xamarin', 'swift', 'kotlin'],
            'design': ['figma', 'sketch', 'adobe xd', 'photoshop', 'illustrator', 'ui/ux', 'wireframing'],
            'soft_skills': ['leadership', 'communication', 'teamwork', 'problem solving', 'critical thinking', 'creativity', 'adaptability']
        }
    
    def extract_skills(self, text):
        """Extract skills from text using NLP and pattern matching"""
        text_lower = text.lower()
        found_skills = []
        
        # Extract using skill database
        for category, skills in self.tech_skills.items():
            for skill in skills:
                if skill in text_lower:
                    found_skills.append(skill)
        
        # Extract using NLP entities
        doc = self.nlp(text)
        for ent in doc.ents:
            if ent.label_ in ["ORG", "PRODUCT", "TECHNOLOGY"]:
                found_skills.append(ent.text.lower())
        
        # Remove duplicates and return
        return list(set(found_skills))
    
    def extract_experience_years(self, text):
        """Extract years of experience from text"""
        patterns = [
            r'(\d+)\+?\s*years?\s*(?:of\s*)?experience',
            r'experience\s*(?:of\s*)?\s*(\d+)\+?\s*years?',
            r'(\d+)\+?\s*years?\s*(?:of\s*)?professional',
            r'(\d+)\+?\s*yrs?\s*exp',
        ]
        
        for pattern in patterns:
            match = re.search(pattern, text.lower())
            if match:
                return int(match.group(1))
        
        # Check for "X to Y years"
        range_pattern = r'(\d+)\s*to\s*(\d+)\s*years?'
        match = re.search(range_pattern, text.lower())
        if match:
            return (int(match.group(1)) + int(match.group(2))) // 2
        
        return 0
    
    def calculate_location_score(self, candidate_location, job_location):
        """Calculate location compatibility score"""
        if not candidate_location or not job_location:
            return 0.5  # Neutral score if location missing
        
        # Check for remote work
        if 'remote' in candidate_location.lower() or 'remote' in job_location.lower():
            return 1.0
        
        try:
            # Get coordinates
            loc1 = self.geolocator.geocode(candidate_location)
            loc2 = self.geolocator.geocode(job_location)
            
            if loc1 and loc2:
                # Calculate distance
                distance = geodesic(
                    (loc1.latitude, loc1.longitude),
                    (loc2.latitude, loc2.longitude)
                ).kilometers
                
                # Score based on distance
                if distance < 50:
                    return 1.0
                elif distance < 100:
                    return 0.8
                elif distance < 500:
                    return 0.5
                else:
                    return 0.2
            else:
                # Fallback to string matching
                if candidate_location.lower() == job_location.lower():
                    return 1.0
                elif any(part in job_location.lower() for part in candidate_location.lower().split()):
                    return 0.7
                else:
                    return 0.3
        except:
            # Simple string matching as fallback
            if candidate_location.lower() == job_location.lower():
                return 1.0
            else:
                return 0.3
    
    def calculate_skills_match(self, candidate_skills, required_skills):
        """Calculate skills matching score"""
        if not candidate_skills or not required_skills:
            return 0.0
        
        candidate_set = set([s.lower() for s in candidate_skills])
        required_set = set([s.lower() for s in required_skills])
        
        if not required_set:
            return 1.0
        
        matched = len(candidate_set.intersection(required_set))
        total_required = len(required_set)
        
        return matched / total_required
    
    def calculate_semantic_similarity(self, text1, text2):
        """Calculate semantic similarity between two texts"""
        if not text1 or not text2:
            return 0.0
        
        # Generate embeddings
        embeddings = self.sentence_model.encode([text1, text2])
        
        # Calculate cosine similarity
        similarity = cosine_similarity([embeddings[0]], [embeddings[1]])[0][0]
        
        return similarity
    
    def find_matches(self, job_data, candidates_df, top_n=10):
        """Find top matching candidates for a job"""
        matches = []
        
        # Extract job requirements
        job_description = job_data.get('job_description', '')
        required_skills_text = job_data.get('required_skills', '')
        job_title = job_data.get('job_title', '')
        job_location = job_data.get('location', '')
        required_experience = self.extract_experience_years(
            job_description + ' ' + str(job_data.get('experience_required', ''))
        )
        
        # Extract required skills
        required_skills = self.extract_skills(
            job_description + ' ' + required_skills_text + ' ' + job_title
        )
        
        # Create job profile text
        job_profile = f"{job_title} {job_description} {required_skills_text}"
        
        for _, candidate in candidates_df.iterrows():
            # Skip if candidate data is incomplete
            if not candidate.get('full_name'):
                continue
            
            # Extract candidate information
            candidate_skills_text = str(candidate.get('skills', ''))
            candidate_experience_text = str(candidate.get('profile_summary', ''))
            candidate_position = str(candidate.get('current_position', ''))
            candidate_location = str(candidate.get('location', ''))
            
            # Extract candidate skills
            candidate_skills = self.extract_skills(
                candidate_skills_text + ' ' + candidate_experience_text + ' ' + candidate_position
            )
            
            # Extract candidate experience years
            candidate_experience_years = self.extract_experience_years(
                candidate_experience_text + ' ' + str(candidate.get('years_experience', ''))
            )
            
            # Create candidate profile text
            candidate_profile = f"{candidate_position} {candidate_skills_text} {candidate_experience_text}"
            
            # Calculate different matching scores
            skills_score = self.calculate_skills_match(candidate_skills, required_skills)
            semantic_score = self.calculate_semantic_similarity(job_profile, candidate_profile)
            location_score = self.calculate_location_score(candidate_location, job_location)
            
            # Experience score
            if required_experience > 0:
                if candidate_experience_years >= required_experience:
                    experience_score = 1.0
                else:
                    experience_score = candidate_experience_years / required_experience
            else:
                experience_score = 1.0
            
            # Calculate weighted final score
            final_score = (
                skills_score * 0.35 +
                semantic_score * 0.30 +
                experience_score * 0.20 +
                location_score * 0.15
            )
            
            # Create match result
            match_result = {
                'candidate_id': candidate.get('candidate_id', 'Unknown'),
                'name': candidate.get('full_name', 'Unknown'),
                'email': candidate.get('email', ''),
                'current_position': candidate.get('current_position', ''),
                'years_experience': candidate_experience_years,
                'location': candidate_location,
                'match_percentage': round(final_score * 100, 2),
                'skills_match': round(skills_score * 100, 2),
                'experience_match': round(experience_score * 100, 2),
                'location_match': round(location_score * 100, 2),
                'matching_skills': list(set(candidate_skills).intersection(set(required_skills))),
                'missing_skills': list(set(required_skills) - set(candidate_skills)),
                'additional_skills': list(set(candidate_skills) - set(required_skills))
            }
            
            matches.append(match_result)
        
        # Sort by match percentage
        matches.sort(key=lambda x: x['match_percentage'], reverse=True)
        
        # Return top N matches
        return matches[:top_n]
    
    def get_skill_recommendations(self, candidate_data, job_market_data=None):
        """Recommend skills for a candidate to improve marketability"""
        current_skills = self.extract_skills(
            str(candidate_data.get('skills', '')) + ' ' + 
            str(candidate_data.get('profile_summary', ''))
        )
        
        # Get all skills from tech_skills database
        all_skills = []
        for category, skills in self.tech_skills.items():
            all_skills.extend(skills)
        
        # Find complementary skills based on current skills
        recommendations = []
        
        # If candidate has programming skills, recommend related frameworks
        if any(skill in current_skills for skill in ['python', 'java', 'javascript']):
            web_frameworks = ['django', 'flask', 'react', 'angular', 'spring']
            recommendations.extend([s for s in web_frameworks if s not in current_skills])
        
        # If candidate has data skills, recommend ML/AI tools
        if any(skill in current_skills for skill in ['python', 'r', 'sql']):
            data_tools = ['tensorflow', 'pytorch', 'pandas', 'scikit-learn']
            recommendations.extend([s for s in data_tools if s not in current_skills])
        
        # Remove duplicates and limit recommendations
        recommendations = list(set(recommendations))[:5]
        
        return recommendations
    
    def calculate_salary_match(self, candidate_expected, job_salary_range):
        """Calculate salary expectation match"""
        if not candidate_expected or not job_salary_range:
            return 0.5  # Neutral score if data missing
        
        try:
            # Parse salary range (e.g., "$80,000 - $120,000")
            salary_match = re.search(r'(\d+).*?(\d+)', job_salary_range.replace(',', ''))
            if salary_match:
                min_salary = int(salary_match.group(1))
                max_salary = int(salary_match.group(2))
                
                # Parse candidate expectation
                candidate_salary = int(re.sub(r'[^\d]', '', str(candidate_expected)))
                
                if min_salary <= candidate_salary <= max_salary:
                    return 1.0
                elif candidate_salary < min_salary:
                    return candidate_salary / min_salary
                else:
                    return max_salary / candidate_salary
        except:
            return 0.5
        
        return 0.5
