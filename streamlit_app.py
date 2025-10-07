import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime, timedelta
import sqlite3
import hashlib
import json
from io import BytesIO

# Page configuration
st.set_page_config(
    page_title="BuffaloMitra - AI-Powered Dairy Management",
    page_icon="🐃",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Initialize Anthropic client
@st.cache_resource
def get_anthropic_client():
    try:
        from anthropic import Anthropic
        api_key = None
        try:
            api_key = st.secrets["ANTHROPIC_API_KEY"]
        except KeyError:
            try:
                api_key = st.secrets["api_keys"]["ANTHROPIC_API_KEY"]
            except KeyError:
                st.error("Could not find ANTHROPIC_API_KEY in secrets.")
                return None
        if api_key:
            return Anthropic(api_key=api_key)
        else:
            st.error("ANTHROPIC_API_KEY is empty")
            return None
    except ImportError:
        st.error("anthropic package not installed. Check requirements.txt")
        return None
    except Exception as e:
        st.error(f"Error initializing AI: {str(e)}")
        return None

# Enhanced Custom CSS
st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap');
    
    * {
        font-family: 'Inter', sans-serif;
    }
    
    .main {
        background: linear-gradient(135deg, #f5f7fa 0%, #c3cfe2 100%);
    }
    
    .main-header {
        font-size: 3.2rem;
        font-weight: 700;
        color: #ffffff;
        text-align: center;
        padding: 2.5rem;
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        border-radius: 20px;
        margin-bottom: 2rem;
        box-shadow: 0 10px 30px rgba(102, 126, 234, 0.3);
    }
    
    .sub-header {
        font-size: 2rem;
        color: #2c3e50;
        font-weight: 700;
        margin-top: 2rem;
        margin-bottom: 1rem;
        border-bottom: 4px solid #667eea;
        padding-bottom: 0.8rem;
    }
    
    .info-card {
        background: linear-gradient(135deg, #ffffff 0%, #f8f9fa 100%);
        padding: 2rem;
        border-radius: 16px;
        border-left: 6px solid #667eea;
        margin: 1.5rem 0;
        box-shadow: 0 8px 24px rgba(0,0,0,0.12);
        transition: transform 0.3s ease;
    }
    
    .info-card:hover {
        transform: translateY(-5px);
        box-shadow: 0 12px 32px rgba(0,0,0,0.18);
    }
    
    .health-card {
        background: linear-gradient(135deg, #ffffff 0%, #e8f5e9 100%);
        padding: 1.8rem;
        border-radius: 16px;
        margin: 1rem 0;
        box-shadow: 0 6px 20px rgba(76, 175, 80, 0.15);
        border: 2px solid #81c784;
    }
    
    .ai-card {
        background: linear-gradient(135deg, #fff8e1 0%, #ffe0b2 100%);
        padding: 2rem;
        border-radius: 16px;
        border-left: 6px solid #ff9800;
        margin: 1.5rem 0;
        box-shadow: 0 8px 24px rgba(255, 152, 0, 0.2);
    }
    
    .alert-card {
        background: linear-gradient(135deg, #ffebee 0%, #ffcdd2 100%);
        padding: 1.8rem;
        border-radius: 16px;
        border-left: 6px solid #f44336;
        margin: 1.2rem 0;
        box-shadow: 0 6px 20px rgba(244, 67, 54, 0.2);
        font-weight: 600;
        color: #c62828;
    }
    
    .success-card {
        background: linear-gradient(135deg, #e8f5e9 0%, #c8e6c9 100%);
        padding: 1.8rem;
        border-radius: 16px;
        border-left: 6px solid #4caf50;
        margin: 1.2rem 0;
        box-shadow: 0 6px 20px rgba(76, 175, 80, 0.2);
        font-weight: 600;
        color: #2e7d32;
    }
    
    .warning-card {
        background: linear-gradient(135deg, #fffde7 0%, #fff9c4 100%);
        padding: 1.8rem;
        border-radius: 16px;
        border-left: 6px solid #ffc107;
        margin: 1.2rem 0;
        box-shadow: 0 6px 20px rgba(255, 193, 7, 0.2);
        font-weight: 600;
        color: #f57f17;
    }
    
    div[data-testid="metric-container"] {
        background: linear-gradient(135deg, #ffffff 0%, #f8f9fa 100%);
        border-radius: 16px;
        padding: 1.5rem;
        box-shadow: 0 6px 20px rgba(0,0,0,0.1);
        border: 2px solid #e3e8ef;
        transition: all 0.3s ease;
    }
    
    div[data-testid="metric-container"]:hover {
        transform: translateY(-5px);
        box-shadow: 0 10px 30px rgba(0,0,0,0.15);
        border-color: #667eea;
    }
    
    .stButton > button {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        color: white;
        border: none;
        border-radius: 12px;
        padding: 0.75rem 2rem;
        font-weight: 600;
        transition: all 0.3s ease;
        box-shadow: 0 4px 15px rgba(102, 126, 234, 0.3);
    }
    
    .stButton > button:hover {
        transform: translateY(-2px);
        box-shadow: 0 8px 25px rgba(102, 126, 234, 0.4);
    }
    
    section[data-testid="stSidebar"] {
        background: linear-gradient(180deg, #2c3e50 0%, #34495e 100%);
    }
    
    section[data-testid="stSidebar"] * {
        color: #ecf0f1 !important;
    }
    
    .dataframe thead tr th {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%) !important;
        color: white !important;
        font-weight: 700 !important;
        padding: 1rem !important;
    }
    </style>
    """, unsafe_allow_html=True)


# Buffalo Breed Database
BUFFALO_BREEDS = {
    "Murrah": {
        "origin": "Punjab, Haryana",
        "avg_milk_yield_liters_per_day": "10-15",
        "peak_yield_liters": "18-22",
        "lactation_period_days": "280-305",
        "fat_percentage": "7-8%",
        "snf_percentage": "9-10%",
        "calving_interval_months": "14-16",
        "first_calving_age_months": "36-40",
        "body_weight_kg": "500-650",
        "characteristics": "Black color, tightly curled horns, wedge-shaped body",
        "price_range_inr": "₹80,000-1,50,000",
        "maintenance_level": "Medium",
        "heat_tolerance": "Good",
        "disease_resistance": "High",
        "suitable_regions": ["Punjab", "Haryana", "Maharashtra", "Gujarat", "Rajasthan"]
    },
    "Mehsana": {
        "origin": "Gujarat",
        "avg_milk_yield_liters_per_day": "8-12",
        "peak_yield_liters": "15-18",
        "lactation_period_days": "270-300",
        "fat_percentage": "7-8%",
        "snf_percentage": "9-10%",
        "calving_interval_months": "14-15",
        "first_calving_age_months": "38-42",
        "body_weight_kg": "450-550",
        "characteristics": "Black to grey color, medium horns",
        "price_range_inr": "₹60,000-1,20,000",
        "maintenance_level": "Low",
        "heat_tolerance": "Excellent",
        "disease_resistance": "High",
        "suitable_regions": ["Gujarat", "Rajasthan", "Maharashtra"]
    },
    "Jaffarabadi": {
        "origin": "Gujarat",
        "avg_milk_yield_liters_per_day": "10-14",
        "peak_yield_liters": "18-20",
        "lactation_period_days": "280-300",
        "fat_percentage": "7-9%",
        "snf_percentage": "9-11%",
        "calving_interval_months": "15-17",
        "first_calving_age_months": "40-45",
        "body_weight_kg": "600-800",
        "characteristics": "Large sized, black color, massive build",
        "price_range_inr": "₹1,00,000-2,00,000",
        "maintenance_level": "High",
        "heat_tolerance": "Good",
        "disease_resistance": "Medium",
        "suitable_regions": ["Gujarat", "Maharashtra", "Karnataka"]
    },
    "Surti": {
        "origin": "Gujarat",
        "avg_milk_yield_liters_per_day": "7-10",
        "peak_yield_liters": "12-15",
        "lactation_period_days": "270-290",
        "fat_percentage": "7-8%",
        "snf_percentage": "9-10%",
        "calving_interval_months": "14-15",
        "first_calving_age_months": "36-40",
        "body_weight_kg": "400-500",
        "characteristics": "Small to medium size, light colored",
        "price_range_inr": "₹50,000-1,00,000",
        "maintenance_level": "Low",
        "heat_tolerance": "Excellent",
        "disease_resistance": "High",
        "suitable_regions": ["Gujarat", "Maharashtra", "Rajasthan"]
    },
    "Nagpuri": {
        "origin": "Maharashtra",
        "avg_milk_yield_liters_per_day": "6-9",
        "peak_yield_liters": "12-14",
        "lactation_period_days": "260-280",
        "fat_percentage": "7-8%",
        "snf_percentage": "9-10%",
        "calving_interval_months": "14-16",
        "first_calving_age_months": "38-42",
        "body_weight_kg": "450-550",
        "characteristics": "Well adapted to Maharashtra climate",
        "price_range_inr": "₹45,000-90,000",
        "maintenance_level": "Low",
        "heat_tolerance": "Excellent",
        "disease_resistance": "High",
        "suitable_regions": ["Maharashtra", "Madhya Pradesh"]
    }
}

# Feed Database
FEED_DATABASE = {
    "Green_Fodder": {
        "items": ["Berseem", "Maize", "Jowar", "Bajra", "Lucerne", "Napier Grass", "Guinea Grass"],
        "requirement_kg_per_day": "25-35",
        "cost_per_kg": "₹2-4",
        "benefits": "High moisture, good palatability, rich in vitamins"
    },
    "Dry_Fodder": {
        "items": ["Wheat Straw", "Paddy Straw", "Sorghum Stover", "Groundnut Haulms"],
        "requirement_kg_per_day": "8-12",
        "cost_per_kg": "₹3-5",
        "benefits": "Bulk feed, provides fiber"
    },
    "Concentrate": {
        "items": ["Cattle Feed", "Cotton Seed Cake", "Groundnut Cake", "Soybean Meal", "Maize", "Wheat Bran"],
        "requirement_kg_per_day": "3-5 (based on milk yield)",
        "cost_per_kg": "₹20-35",
        "formula": "1 kg concentrate per 2.5 liters milk production",
        "benefits": "High energy, protein, increases milk yield"
    },
    "Mineral_Mixture": {
        "items": ["Commercial Mineral Mix", "Salt"],
        "requirement_kg_per_day": "0.05-0.1",
        "cost_per_kg": "₹40-60",
        "benefits": "Prevents deficiencies, improves reproduction"
    }
}

# Disease Database
DISEASE_DATABASE = {
    "Mastitis": {
        "type": "Bacterial",
        "symptoms": ["Swollen udder", "Hot and painful quarter", "Watery or clotted milk", "Reduced milk yield"],
        "prevention": ["Proper milking hygiene", "Teat dipping", "Clean environment", "Regular udder examination"],
        "treatment": ["Antibiotics (Veterinary)", "Strip milking", "Hot fomentation", "Anti-inflammatory drugs"],
        "critical": True
    },
    "Foot and Mouth Disease": {
        "type": "Viral",
        "symptoms": ["Fever", "Blisters in mouth and feet", "Drooling", "Lameness", "Reduced feed intake"],
        "prevention": ["Vaccination (twice yearly)", "Isolation of sick animals", "Farm biosecurity"],
        "treatment": ["Supportive care", "Wound care", "Soft feed", "Consult veterinarian immediately"],
        "critical": True
    },
    "Hemorrhagic Septicemia": {
        "type": "Bacterial",
        "symptoms": ["High fever", "Difficulty breathing", "Swelling in throat", "Sudden death"],
        "prevention": ["Annual vaccination", "Avoid waterlogging", "Good hygiene"],
        "treatment": ["Emergency veterinary care", "Antibiotics", "Supportive therapy"],
        "critical": True
    },
    "Repeat Breeding": {
        "type": "Reproductive",
        "symptoms": ["Regular heat but no conception", "More than 3 AI attempts fail"],
        "prevention": ["Proper nutrition", "Minerals supplementation", "Timely AI", "Health check-up"],
        "treatment": ["Hormonal therapy", "Uterine infection treatment", "Veterinary examination"],
        "critical": False
    },
    "Bloat": {
        "type": "Digestive",
        "symptoms": ["Distended left side", "Difficulty breathing", "Restlessness", "Stop ruminating"],
        "prevention": ["Gradual diet change", "Avoid wet green fodder", "Provide dry roughage"],
        "treatment": ["Stomach tube", "Bloat oil", "Walking", "Emergency: veterinary puncture"],
        "critical": True
    }
}

# Government Schemes
GOVERNMENT_SCHEMES = {
    "National_Dairy_Plan": {
        "name": "National Dairy Plan (NDP)",
        "benefit": "Productivity enhancement, breed improvement",
        "eligibility": "Dairy farmers, cooperatives",
        "how_to_apply": "Through State Implementing Agencies",
        "contact": "https://www.nddb.coop"
    },
    "Dairy_Entrepreneurship_Development": {
        "name": "Dairy Entrepreneurship Development Scheme (DEDS)",
        "benefit": "Subsidy for dairy units (25-33%)",
        "eligibility": "Individual/group wanting to start dairy",
        "how_to_apply": "Through NABARD",
        "contact": "https://www.nabard.org"
    },
    "Rashtriya_Gokul_Mission": {
        "name": "Rashtriya Gokul Mission",
        "benefit": "Breed conservation, development",
        "eligibility": "Farmers with indigenous breeds",
        "how_to_apply": "Through State Animal Husbandry Department",
        "contact": "State AH Department"
    },
    "Kisan_Credit_Card_Dairy": {
        "name": "Kisan Credit Card (Dairy)",
        "benefit": "Credit for dairy farming at 4% interest",
        "eligibility": "All dairy farmers",
        "how_to_apply": "Any bank",
        "contact": "Nearest bank branch"
    }
}

# Vaccination Schedule Template
VACCINATION_SCHEDULE = {
    "FMD": {"frequency_months": 6, "name": "Foot and Mouth Disease", "critical": True},
    "HS": {"frequency_months": 12, "name": "Hemorrhagic Septicemia", "critical": True},
    "BQ": {"frequency_months": 12, "name": "Black Quarter", "critical": True},
    "Brucellosis": {"frequency_months": 12, "name": "Brucellosis", "critical": False},
    "Deworming": {"frequency_months": 4, "name": "Deworming", "critical": True}
}

# Database initialization
def init_database():
    conn = sqlite3.connect('buffalomitra.db', check_same_thread=False)
    c = conn.cursor()
    
    c.execute('''CREATE TABLE IF NOT EXISTS users
                 (id INTEGER PRIMARY KEY AUTOINCREMENT,
                  username TEXT UNIQUE NOT NULL,
                  password_hash TEXT NOT NULL,
                  full_name TEXT NOT NULL,
                  mobile TEXT NOT NULL,
                  email TEXT,
                  district TEXT,
                  village TEXT,
                  user_type TEXT DEFAULT 'Dairy Farmer',
                  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP)''')
    
    c.execute('''CREATE TABLE IF NOT EXISTS buffalo_inventory
                 (id INTEGER PRIMARY KEY AUTOINCREMENT,
                  user_id INTEGER,
                  tag_number TEXT UNIQUE,
                  name TEXT,
                  breed TEXT,
                  date_of_birth DATE,
                  purchase_date DATE,
                  purchase_price REAL,
                  current_lactation INTEGER DEFAULT 0,
                  status TEXT DEFAULT 'Active',
                  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                  FOREIGN KEY(user_id) REFERENCES users(id))''')
    
    c.execute('''CREATE TABLE IF NOT EXISTS milk_production
                 (id INTEGER PRIMARY KEY AUTOINCREMENT,
                  user_id INTEGER,
                  buffalo_id INTEGER,
                  date DATE,
                  morning_yield REAL,
                  evening_yield REAL,
                  total_yield REAL,
                  fat_percentage REAL,
                  price_per_liter REAL,
                  notes TEXT,
                  FOREIGN KEY(user_id) REFERENCES users(id),
                  FOREIGN KEY(buffalo_id) REFERENCES buffalo_inventory(id))''')
    
    c.execute('''CREATE TABLE IF NOT EXISTS breeding_records
                 (id INTEGER PRIMARY KEY AUTOINCREMENT,
                  user_id INTEGER,
                  buffalo_id INTEGER,
                  breeding_date DATE,
                  breeding_type TEXT,
                  bull_details TEXT,
                  expected_calving_date DATE,
                  actual_calving_date DATE,
                  calf_gender TEXT,
                  pregnancy_status TEXT DEFAULT 'Bred',
                  notes TEXT,
                  FOREIGN KEY(user_id) REFERENCES users(id),
                  FOREIGN KEY(buffalo_id) REFERENCES buffalo_inventory(id))''')
    
    c.execute('''CREATE TABLE IF NOT EXISTS health_records
                 (id INTEGER PRIMARY KEY AUTOINCREMENT,
                  user_id INTEGER,
                  buffalo_id INTEGER,
                  date DATE,
                  record_type TEXT,
                  disease_name TEXT,
                  symptoms TEXT,
                  treatment TEXT,
                  medicine TEXT,
                  veterinarian TEXT,
                  cost REAL,
                  follow_up_date DATE,
                  notes TEXT,
                  FOREIGN KEY(user_id) REFERENCES users(id),
                  FOREIGN KEY(buffalo_id) REFERENCES buffalo_inventory(id))''')
    
    c.execute('''CREATE TABLE IF NOT EXISTS feed_management
                 (id INTEGER PRIMARY KEY AUTOINCREMENT,
                  user_id INTEGER,
                  date DATE,
                  feed_type TEXT,
                  quantity_kg REAL,
                  cost_per_kg REAL,
                  total_cost REAL,
                  supplier TEXT,
                  notes TEXT,
                  FOREIGN KEY(user_id) REFERENCES users(id))''')
    
    c.execute('''CREATE TABLE IF NOT EXISTS financial_records
                 (id INTEGER PRIMARY KEY AUTOINCREMENT,
                  user_id INTEGER,
                  date DATE,
                  category TEXT,
                  transaction_type TEXT,
                  amount REAL,
                  description TEXT,
                  FOREIGN KEY(user_id) REFERENCES users(id))''')
    
    c.execute('''CREATE TABLE IF NOT EXISTS milk_buyers
                 (id INTEGER PRIMARY KEY AUTOINCREMENT,
                  user_id INTEGER,
                  buyer_name TEXT,
                  contact TEXT,
                  price_per_liter REAL,
                  payment_terms TEXT,
                  active BOOLEAN DEFAULT 1,
                  FOREIGN KEY(user_id) REFERENCES users(id))''')
    
    # NEW TABLES
    c.execute('''CREATE TABLE IF NOT EXISTS calf_records
                 (id INTEGER PRIMARY KEY AUTOINCREMENT,
                  user_id INTEGER,
                  mother_buffalo_id INTEGER,
                  tag_number TEXT UNIQUE,
                  name TEXT,
                  date_of_birth DATE,
                  gender TEXT,
                  birth_weight REAL,
                  breed TEXT,
                  status TEXT DEFAULT 'Active',
                  weaning_date DATE,
                  sale_date DATE,
                  sale_price REAL,
                  notes TEXT,
                  FOREIGN KEY(user_id) REFERENCES users(id),
                  FOREIGN KEY(mother_buffalo_id) REFERENCES buffalo_inventory(id))''')
    
    c.execute('''CREATE TABLE IF NOT EXISTS heat_detection
                 (id INTEGER PRIMARY KEY AUTOINCREMENT,
                  user_id INTEGER,
                  buffalo_id INTEGER,
                  heat_date DATE,
                  heat_intensity TEXT,
                  bred BOOLEAN DEFAULT 0,
                  breeding_id INTEGER,
                  notes TEXT,
                  FOREIGN KEY(user_id) REFERENCES users(id),
                  FOREIGN KEY(buffalo_id) REFERENCES buffalo_inventory(id))''')
    
    c.execute('''CREATE TABLE IF NOT EXISTS vaccination_records
                 (id INTEGER PRIMARY KEY AUTOINCREMENT,
                  user_id INTEGER,
                  buffalo_id INTEGER,
                  vaccination_type TEXT,
                  date DATE,
                  next_due_date DATE,
                  veterinarian TEXT,
                  cost REAL,
                  batch_number TEXT,
                  notes TEXT,
                  FOREIGN KEY(user_id) REFERENCES users(id),
                  FOREIGN KEY(buffalo_id) REFERENCES buffalo_inventory(id))''')
    
    c.execute('''CREATE TABLE IF NOT EXISTS feed_inventory
                 (id INTEGER PRIMARY KEY AUTOINCREMENT,
                  user_id INTEGER,
                  feed_name TEXT,
                  feed_type TEXT,
                  current_stock_kg REAL,
                  reorder_level_kg REAL,
                  last_purchase_date DATE,
                  last_purchase_quantity REAL,
                  last_purchase_cost REAL,
                  supplier TEXT,
                  FOREIGN KEY(user_id) REFERENCES users(id))''')
    
    c.execute('''CREATE TABLE IF NOT EXISTS alerts
                 (id INTEGER PRIMARY KEY AUTOINCREMENT,
                  user_id INTEGER,
                  alert_type TEXT,
                  buffalo_id INTEGER,
                  alert_date DATE,
                  message TEXT,
                  priority TEXT,
                  resolved BOOLEAN DEFAULT 0,
                  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                  FOREIGN KEY(user_id) REFERENCES users(id))''')
    
    c.execute('''CREATE TABLE IF NOT EXISTS labor_records
                 (id INTEGER PRIMARY KEY AUTOINCREMENT,
                  user_id INTEGER,
                  worker_name TEXT,
                  contact TEXT,
                  role TEXT,
                  monthly_salary REAL,
                  join_date DATE,
                  active BOOLEAN DEFAULT 1,
                  FOREIGN KEY(user_id) REFERENCES users(id))''')
    
    conn.commit()
    conn.close()

def hash_password(password):
    return hashlib.sha256(password.encode()).hexdigest()

def create_user(username, password, full_name, mobile, email, district, village, user_type='Dairy Farmer'):
    try:
        conn = sqlite3.connect('buffalomitra.db')
        c = conn.cursor()
        password_hash = hash_password(password)
        c.execute('''INSERT INTO users (username, password_hash, full_name, mobile, email, 
                     district, village, user_type)
                     VALUES (?, ?, ?, ?, ?, ?, ?, ?)''',
                  (username, password_hash, full_name, mobile, email, district, village, user_type))
        conn.commit()
        user_id = c.lastrowid
        conn.close()
        return True, user_id
    except sqlite3.IntegrityError:
        return False, "Username already exists"
    except Exception as e:
        return False, str(e)

def authenticate_user(username, password):
    conn = sqlite3.connect('buffalomitra.db')
    c = conn.cursor()
    password_hash = hash_password(password)
    c.execute('''SELECT id, username, full_name, mobile, email, district, village, user_type
                 FROM users WHERE username=? AND password_hash=?''',
              (username, password_hash))
    user = c.fetchone()
    conn.close()
    if user:
        return {
            'id': user[0], 'username': user[1], 'full_name': user[2],
            'mobile': user[3], 'email': user[4], 'district': user[5],
            'village': user[6], 'user_type': user[7]
        }
    return None

def get_ai_response(user_message, context=""):
    client = get_anthropic_client()
    if not client:
        return "AI Assistant is not configured. Please add ANTHROPIC_API_KEY to secrets."
    
    try:
        user_data = st.session_state.get('user_data', {})
        location = f"{user_data.get('village', 'Unknown')}, {user_data.get('district', 'India')}"
        
        system_prompt = f"""You are BuffaloMitra AI, an expert buffalo dairy farming advisor.

Current farmer context:
- Location: {location}

You provide:
1. Buffalo breed selection and management advice
2. Feeding and nutrition recommendations
3. Breeding and reproduction guidance
4. Disease prevention and treatment advice
5. Milk production optimization
6. Financial and business advice for dairy farming
7. Government schemes and subsidies information

Always be:
- Practical and actionable
- Specific to Indian dairy farming conditions
- Supportive and encouraging
- Data-driven with realistic expectations

{context}"""
        
        message = client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=1500,
            system=system_prompt,
            messages=[
                {"role": "user", "content": user_message}
            ]
        )
        
        return message.content[0].text
    except Exception as e:
        return f"Sorry, I encountered an error: {str(e)}"

def generate_alerts(user_id):
    """Generate alerts for upcoming events"""
    conn = sqlite3.connect('buffalomitra.db')
    c = conn.cursor()
    today = datetime.now().date()
    
    # Check for upcoming calvings
    c.execute("""SELECT br.id, bi.name, bi.tag_number, br.expected_calving_date
                 FROM breeding_records br
                 JOIN buffalo_inventory bi ON br.buffalo_id = bi.id
                 WHERE br.user_id=? AND br.pregnancy_status='Pregnant' 
                 AND br.expected_calving_date BETWEEN ? AND ?""",
              (user_id, today, today + timedelta(days=30)))
    calvings = c.fetchall()
    
    # Check for vaccination due
    c.execute("""SELECT vr.id, bi.name, bi.tag_number, vr.vaccination_type, vr.next_due_date
                 FROM vaccination_records vr
                 JOIN buffalo_inventory bi ON vr.buffalo_id = bi.id
                 WHERE vr.user_id=? AND vr.next_due_date BETWEEN ? AND ?""",
              (user_id, today, today + timedelta(days=15)))
    vaccinations = c.fetchall()
    
    # Check for low feed stock
    c.execute("""SELECT feed_name, current_stock_kg, reorder_level_kg
                 FROM feed_inventory
                 WHERE user_id=? AND current_stock_kg <= reorder_level_kg""",
              (user_id,))
    low_stock = c.fetchall()
    
    conn.close()
    
    alerts = []
    for calving in calvings:
        days_until = (calving[3] - today).days
        alerts.append({
            'type': 'calving',
            'priority': 'high' if days_until <= 7 else 'medium',
            'message': f"{calving[1]} ({calving[2]}) - Expected calving in {days_until} days"
        })
    
    for vacc in vaccinations:
        days_until = (vacc[4] - today).days
        alerts.append({
            'type': 'vaccination',
            'priority': 'high' if days_until <= 3 else 'medium',
            'message': f"{vacc[1]} ({vacc[2]}) - {vacc[3]} due in {days_until} days"
        })
    
    for stock in low_stock:
        alerts.append({
            'type': 'feed',
            'priority': 'high',
            'message': f"Low stock: {stock[0]} - Only {stock[1]:.1f} kg remaining"
        })
    
    return alerts

# Session state initialization
if 'user_data' not in st.session_state:
    st.session_state.user_data = None
if 'current_page' not in st.session_state:
    st.session_state.current_page = "Dashboard"
if 'chat_history' not in st.session_state:
    st.session_state.chat_history = []

def main():
    init_database()
    st.markdown('<div class="main-header">🐃 BuffaloMitra - AI Powered Dairy Management</div>', unsafe_allow_html=True)
    st.markdown("### संपूर्ण म्हैस व्यवस्थापन प्रणाली | Complete Buffalo Dairy Management System")
    
    if st.session_state.user_data is None:
        show_auth_page()
    else:
        show_main_app()

def show_auth_page():
    tab1, tab2 = st.tabs(["Login", "Register"])
    
    with tab1:
        st.markdown("### Login")
        with st.form("login_form"):
            username = st.text_input("Username")
            password = st.text_input("Password", type="password")
            submitted = st.form_submit_button("Login", use_container_width=True, type="primary")
            
            if submitted:
                if username and password:
                    user = authenticate_user(username, password)
                    if user:
                        st.session_state.user_data = user
                        st.success(f"Welcome {user['full_name']}!")
                        st.rerun()
                    else:
                        st.error("Invalid credentials")
                else:
                    st.warning("Please fill all fields")
    
    with tab2:
        st.markdown("### Create Account")
        with st.form("register_form"):
            col1, col2 = st.columns(2)
            with col1:
                new_username = st.text_input("Username*")
                new_password = st.text_input("Password* (min 6 chars)", type="password")
                full_name = st.text_input("Full Name*")
                mobile = st.text_input("Mobile* (10 digits)")
            with col2:
                email = st.text_input("Email")
                district = st.text_input("District*")
                village = st.text_input("Village*")
                user_type = st.selectbox("I am a", ["Dairy Farmer", "Buyer/Trader", "Veterinarian"])
            
            submitted = st.form_submit_button("Register", use_container_width=True, type="primary")
            
            if submitted:
                if not all([new_username, new_password, full_name, mobile, district, village]):
                    st.error("Please fill all required fields")
                elif len(new_password) < 6:
                    st.error("Password must be at least 6 characters")
                elif not mobile.isdigit() or len(mobile) != 10:
                    st.error("Please enter valid 10-digit mobile")
                else:
                    success, result = create_user(new_username, new_password, full_name, mobile, 
                                                 email, district, village, user_type)
                    if success:
                        st.success("Account created! Please login")
                    else:
                        st.error(f"Error: {result}")

def show_main_app():
    user = st.session_state.user_data
    
    with st.sidebar:
        st.markdown(f"### {user['full_name']}")
        st.markdown(f"**{user['village']}, {user['district']}**")
        st.markdown("---")
        
        # Show alerts count
        alerts = generate_alerts(user['id'])
        if alerts:
            st.markdown(f"### ⚠️ Alerts ({len(alerts)})")
        
        pages = [
            "Dashboard",
            "AI Assistant",
            "Buffalo Inventory",
            "Milk Production Tracker",
            "Breeding Manager",
            "Health Records",
            "Feed Management",
            "Breed Information",
            "Disease Guide",
            "Milk Price Tracker",
            "Financial Manager",
            "Profit Calculator",
            "Government Schemes",
            "Buyer Connect",
            "Insurance Calculator",
            # NEW PAGES
            "Alerts & Reminders",
            "Calf Management",
            "Heat Detection",
            "Vaccination Schedule",
            "Feed Inventory",
            "Labor Management",
            "Advanced Analytics",
            "Reports Generator"
        ]
        
        st.markdown("### Navigation")
        for page in pages:
            if st.button(page, key=f"nav_{page}", use_container_width=True, 
                        type="primary" if st.session_state.current_page == page else "secondary"):
                st.session_state.current_page = page
                st.rerun()
        
        st.markdown("---")
        if st.button("Logout", use_container_width=True):
            st.session_state.user_data = None
            st.session_state.current_page = "Dashboard"
            st.rerun()
    
    # Page routing
    page = st.session_state.current_page
    
    if page == "Dashboard":
        show_dashboard()
    elif page == "AI Assistant":
        show_ai_assistant()
    elif page == "Buffalo Inventory":
        show_buffalo_inventory()
    elif page == "Milk Production Tracker":
        show_milk_production()
    elif page == "Breeding Manager":
        show_breeding_manager()
    elif page == "Health Records":
        show_health_records()
    elif page == "Feed Management":
        show_feed_management()
    elif page == "Breed Information":
        show_breed_information()
    elif page == "Disease Guide":
        show_disease_guide()
    elif page == "Milk Price Tracker":
        show_milk_price_tracker()
    elif page == "Financial Manager":
        show_financial_manager()
    elif page == "Profit Calculator":
        show_profit_calculator()
    elif page == "Government Schemes":
        show_government_schemes()
    elif page == "Buyer Connect":
        show_buyer_connect()
    elif page == "Insurance Calculator":
        show_insurance_calculator()
    elif page == "Alerts & Reminders":
        show_alerts_reminders()
    elif page == "Calf Management":
        show_calf_management()
    elif page == "Heat Detection":
        show_heat_detection()
    elif page == "Vaccination Schedule":
        show_vaccination_schedule()
    elif page == "Feed Inventory":
        show_feed_inventory()
    elif page == "Labor Management":
        show_labor_management()
    elif page == "Advanced Analytics":
        show_advanced_analytics()
    elif page == "Reports Generator":
        show_reports_generator()

def show_dashboard():
    user = st.session_state.user_data
    st.markdown(f"### Welcome, {user['full_name']}!")
    
    # Show critical alerts at top
    alerts = generate_alerts(user['id'])
    high_priority = [a for a in alerts if a['priority'] == 'high']
    
    if high_priority:
        st.markdown("### ⚠️ Urgent Alerts")
        for alert in high_priority:
            st.markdown(f'<div class="alert-card">{alert["message"]}</div>', unsafe_allow_html=True)
    
    # Get statistics
    conn = sqlite3.connect('buffalomitra.db')
    c = conn.cursor()
    
    c.execute("SELECT COUNT(*) FROM buffalo_inventory WHERE user_id=? AND status='Active'", (user['id'],))
    total_buffalo = c.fetchone()[0]
    
    c.execute("SELECT COUNT(*) FROM buffalo_inventory WHERE user_id=? AND current_lactation>0 AND status='Active'", (user['id'],))
    lactating = c.fetchone()[0]
    
    c.execute("""SELECT SUM(total_yield) FROM milk_production 
                 WHERE user_id=? AND date=?""", (user['id'], datetime.now().date()))
    today_milk = c.fetchone()[0] or 0
    
    c.execute("""SELECT AVG(total_yield) FROM milk_production 
                 WHERE user_id=? AND date >= date('now', '-30 days')""", (user['id'],))
    avg_daily = c.fetchone()[0] or 0
    
    c.execute("SELECT COUNT(*) FROM calf_records WHERE user_id=? AND status='Active'", (user['id'],))
    active_calves = c.fetchone()[0]
    
    conn.close()
    
    col1, col2, col3, col4, col5 = st.columns(5)
    with col1:
        st.metric("Total Buffaloes", total_buffalo)
    with col2:
        st.metric("Lactating", lactating)
    with col3:
        st.metric("Today's Milk", f"{today_milk:.1f} L")
    with col4:
        st.metric("30-Day Avg", f"{avg_daily:.1f} L/day")
    with col5:
        st.metric("Active Calves", active_calves)
    
    # Quick actions
    st.markdown("### Quick Actions")
    col1, col2, col3, col4, col5 = st.columns(5)
    with col1:
        if st.button("Record Milk", use_container_width=True):
            st.session_state.current_page = "Milk Production Tracker"
            st.rerun()
    with col2:
        if st.button("Add Buffalo", use_container_width=True):
            st.session_state.current_page = "Buffalo Inventory"
            st.rerun()
    with col3:
        if st.button("Health Check", use_container_width=True):
            st.session_state.current_page = "Health Records"
            st.rerun()
    with col4:
        if st.button("Ask AI", use_container_width=True):
            st.session_state.current_page = "AI Assistant"
            st.rerun()
    with col5:
        if st.button("View Alerts", use_container_width=True):
            st.session_state.current_page = "Alerts & Reminders"
            st.rerun()
    
    # Recent milk production chart
    st.markdown("### Milk Production Trend (Last 30 Days)")
    conn = sqlite3.connect('buffalomitra.db')
    df = pd.read_sql_query(
        """SELECT date, SUM(total_yield) as total 
           FROM milk_production 
           WHERE user_id=? AND date >= date('now', '-30 days')
           GROUP BY date ORDER BY date""",
        conn, params=(user['id'],))
    conn.close()
    
    if not df.empty:
        fig = px.line(df, x='date', y='total', title='Daily Milk Production',
                     labels={'total': 'Milk (Liters)', 'date': 'Date'})
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("No production data yet. Start recording milk production!")

def show_ai_assistant():
    st.markdown("### AI Dairy Assistant")
    st.markdown("Ask me anything about buffalo dairy farming!")
    
    for message in st.session_state.chat_history:
        if message["role"] == "user":
            st.markdown(f'<div class="info-card"><strong>You:</strong> {message["content"]}</div>', 
                       unsafe_allow_html=True)
        else:
            st.markdown(f'<div class="ai-card"><strong>BuffaloMitra AI:</strong> {message["content"]}</div>', 
                       unsafe_allow_html=True)
    
    st.markdown("### Quick Questions")
    col1, col2, col3 = st.columns(3)
    with col1:
        if st.button("Best buffalo breed for my area", use_container_width=True):
            question = f"What is the best buffalo breed for {st.session_state.user_data['district']}?"
            with st.spinner("Thinking..."):
                response = get_ai_response(question)
                st.session_state.chat_history.append({"role": "user", "content": question})
                st.session_state.chat_history.append({"role": "assistant", "content": response})
                st.rerun()
    with col2:
        if st.button("How to increase milk yield", use_container_width=True):
            question = "What are the best practices to increase milk yield in buffaloes?"
            with st.spinner("Analyzing..."):
                response = get_ai_response(question)
                st.session_state.chat_history.append({"role": "user", "content": question})
                st.session_state.chat_history.append({"role": "assistant", "content": response})
                st.rerun()
    with col3:
        if st.button("Disease prevention tips", use_container_width=True):
            question = "What are essential disease prevention practices for buffalo dairy farming?"
            with st.spinner("Searching..."):
                response = get_ai_response(question)
                st.session_state.chat_history.append({"role": "user", "content": question})
                st.session_state.chat_history.append({"role": "assistant", "content": response})
                st.rerun()
    
    with st.form("chat_form", clear_on_submit=True):
        user_input = st.text_area("Your question:", placeholder="E.g., How much concentrate feed should I give?", height=100)
        submitted = st.form_submit_button("Send", use_container_width=True, type="primary")
        
        if submitted and user_input:
            with st.spinner("Getting answer..."):
                response = get_ai_response(user_input)
                st.session_state.chat_history.append({"role": "user", "content": user_input})
                st.session_state.chat_history.append({"role": "assistant", "content": response})
                st.rerun()
    
    if st.session_state.chat_history:
        if st.button("Clear Chat History"):
            st.session_state.chat_history = []
            st.rerun()

def show_buffalo_inventory():
    st.markdown("### Buffalo Inventory")
    user = st.session_state.user_data
    
    tab1, tab2 = st.tabs(["My Buffaloes", "Add New Buffalo"])
    
    with tab1:
        conn = sqlite3.connect('buffalomitra.db')
        c = conn.cursor()
        c.execute("""SELECT id, tag_number, name, breed, date_of_birth, current_lactation, status 
                     FROM buffalo_inventory WHERE user_id=? ORDER BY tag_number""", (user['id'],))
        buffaloes = c.fetchall()
        conn.close()
        
        if buffaloes:
            for buf in buffaloes:
                age = (datetime.now().date() - datetime.strptime(str(buf[4]), '%Y-%m-%d').date()).days // 365
                with st.expander(f"🐃 {buf[2]} (Tag: {buf[1]}) - {buf[3]}"):
                    col1, col2, col3 = st.columns(3)
                    with col1:
                        st.write(f"**Age:** {age} years")
                        st.write(f"**Breed:** {buf[3]}")
                    with col2:
                        st.write(f"**Lactation:** {buf[5]}")
                        st.write(f"**Status:** {buf[6]}")
                    with col3:
                        st.write(f"**DOB:** {buf[4]}")
        else:
            st.info("No buffaloes added yet. Add your first buffalo below!")
    
    with tab2:
        st.markdown("### Add New Buffalo")
        with st.form("add_buffalo"):
            col1, col2 = st.columns(2)
            with col1:
                tag_number = st.text_input("Tag/ID Number*")
                name = st.text_input("Name")
                breed = st.selectbox("Breed*", list(BUFFALO_BREEDS.keys()))
                dob = st.date_input("Date of Birth*")
            with col2:
                purchase_date = st.date_input("Purchase Date")
                purchase_price = st.number_input("Purchase Price (₹)", min_value=0, value=100000)
                current_lactation = st.number_input("Current Lactation Number", min_value=0, value=0)
            
            submitted = st.form_submit_button("Add Buffalo", use_container_width=True, type="primary")
            
            if submitted and tag_number and breed:
                conn = sqlite3.connect('buffalomitra.db')
                c = conn.cursor()
                try:
                    c.execute("""INSERT INTO buffalo_inventory 
                                (user_id, tag_number, name, breed, date_of_birth, 
                                 purchase_date, purchase_price, current_lactation, status)
                                VALUES (?, ?, ?, ?, ?, ?, ?, ?, 'Active')""",
                             (user['id'], tag_number, name, breed, dob, 
                              purchase_date, purchase_price, current_lactation))
                    conn.commit()
                    st.success(f"Buffalo {name or tag_number} added successfully!")
                    st.rerun()
                except sqlite3.IntegrityError:
                    st.error("Tag number already exists!")
                finally:
                    conn.close()

def show_milk_production():
    st.markdown("### Milk Production Tracker")
    user = st.session_state.user_data
    
    tab1, tab2, tab3 = st.tabs(["Record Production", "View Records", "Analysis"])
    
    with tab1:
        conn = sqlite3.connect('buffalomitra.db')
        c = conn.cursor()
        c.execute("""SELECT id, tag_number, name, breed FROM buffalo_inventory 
                     WHERE user_id=? AND current_lactation>0 AND status='Active'""", (user['id'],))
        buffaloes = c.fetchall()
        conn.close()
        
        if buffaloes:
            with st.form("record_milk"):
                buffalo_options = {f"{b[1]} - {b[2]} ({b[3]})": b[0] for b in buffaloes}
                selected = st.selectbox("Select Buffalo", list(buffalo_options.keys()))
                buffalo_id = buffalo_options[selected]
                
                col1, col2 = st.columns(2)
                with col1:
                    date = st.date_input("Date", value=datetime.now())
                    morning_yield = st.number_input("Morning Yield (Liters)", min_value=0.0, value=5.0, step=0.1)
                    evening_yield = st.number_input("Evening Yield (Liters)", min_value=0.0, value=5.0, step=0.1)
                with col2:
                    fat_percentage = st.number_input("Fat %", min_value=0.0, max_value=15.0, value=7.5, step=0.1)
                    price_per_liter = st.number_input("Price per Liter (₹)", min_value=0, value=60)
                    notes = st.text_input("Notes")
                
                submitted = st.form_submit_button("Record", use_container_width=True, type="primary")
                
                if submitted:
                    total_yield = morning_yield + evening_yield
                    conn = sqlite3.connect('buffalomitra.db')
                    c = conn.cursor()
                    c.execute("""INSERT INTO milk_production 
                                (user_id, buffalo_id, date, morning_yield, evening_yield, 
                                 total_yield, fat_percentage, price_per_liter, notes)
                                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                             (user['id'], buffalo_id, date, morning_yield, evening_yield,
                              total_yield, fat_percentage, price_per_liter, notes))
                    conn.commit()
                    conn.close()
                    st.success(f"Recorded: {total_yield:.1f} liters")
                    st.rerun()
        else:
            st.warning("No lactating buffaloes. Update buffalo lactation status in inventory.")
    
    with tab2:
        conn = sqlite3.connect('buffalomitra.db')
        df = pd.read_sql_query(
            """SELECT mp.date, bi.tag_number, bi.name, mp.morning_yield, 
               mp.evening_yield, mp.total_yield, mp.fat_percentage, mp.price_per_liter
               FROM milk_production mp
               JOIN buffalo_inventory bi ON mp.buffalo_id = bi.id
               WHERE mp.user_id=? 
               ORDER BY mp.date DESC LIMIT 100""",
            conn, params=(user['id'],))
        conn.close()
        
        if not df.empty:
            st.dataframe(df, use_container_width=True)
            
            total_milk = df['total_yield'].sum()
            avg_fat = df['fat_percentage'].mean()
            total_value = (df['total_yield'] * df['price_per_liter']).sum()
            
            col1, col2, col3 = st.columns(3)
            with col1:
                st.metric("Total Milk", f"{total_milk:.1f} L")
            with col2:
                st.metric("Avg Fat %", f"{avg_fat:.2f}%")
            with col3:
                st.metric("Total Value", f"₹{total_value:,.0f}")
        else:
            st.info("No production records yet")
    
    with tab3:
        st.markdown("### Production Analysis")
        
        conn = sqlite3.connect('buffalomitra.db')
        df_analysis = pd.read_sql_query(
            """SELECT date, SUM(total_yield) as daily_total, AVG(fat_percentage) as avg_fat
               FROM milk_production 
               WHERE user_id=? AND date >= date('now', '-90 days')
               GROUP BY date ORDER BY date""",
            conn, params=(user['id'],))
        conn.close()
        
        if not df_analysis.empty:
            fig = go.Figure()
            fig.add_trace(go.Bar(x=df_analysis['date'], y=df_analysis['daily_total'],
                                name='Daily Milk', yaxis='y', marker_color='lightblue'))
            fig.add_trace(go.Scatter(x=df_analysis['date'], y=df_analysis['avg_fat'],
                                    name='Fat %', yaxis='y2', mode='lines+markers',
                                    line=dict(color='orange', width=2)))
            
            fig.update_layout(
                title='Milk Production & Fat % Trend',
                xaxis=dict(title='Date'),
                yaxis=dict(title='Milk (Liters)', side='left'),
                yaxis2=dict(title='Fat %', side='right', overlaying='y'),
                hovermode='x unified'
            )
            
            st.plotly_chart(fig, use_container_width=True)

def show_breed_information():
    st.markdown("### Buffalo Breed Information")
    
    breed_name = st.selectbox("Select Breed", list(BUFFALO_BREEDS.keys()))
    breed = BUFFALO_BREEDS[breed_name]
    
    st.markdown(f"## {breed_name}")
    
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("Avg Daily Yield", breed['avg_milk_yield_liters_per_day'] + " L")
        st.metric("Peak Yield", breed['peak_yield_liters'] + " L")
        st.metric("Fat %", breed['fat_percentage'])
    with col2:
        st.metric("Lactation Period", breed['lactation_period_days'] + " days")
        st.metric("Calving Interval", breed['calving_interval_months'] + " months")
        st.metric("First Calving Age", breed['first_calving_age_months'] + " months")
    with col3:
        st.metric("Body Weight", breed['body_weight_kg'] + " kg")
        st.metric("Price Range", breed['price_range_inr'])
        st.metric("Heat Tolerance", breed['heat_tolerance'])
    
    st.markdown("### Characteristics")
    st.info(breed['characteristics'])
    
    st.markdown("### Suitability")
    st.success(f"**Suitable Regions:** {', '.join(breed['suitable_regions'])}")
    st.write(f"**Maintenance Level:** {breed['maintenance_level']}")
    st.write(f"**Disease Resistance:** {breed['disease_resistance']}")

def show_disease_guide():
    st.markdown("### Disease Guide")
    
    for disease_name, disease in DISEASE_DATABASE.items():
        with st.expander(f"{'🔴' if disease['critical'] else '🟡'} {disease_name} ({disease['type']})"):
            st.markdown("#### Symptoms")
            for symptom in disease['symptoms']:
                st.write(f"- {symptom}")
            
            st.markdown("#### Prevention")
            for prevention in disease['prevention']:
                st.success(f"✓ {prevention}")
            
            st.markdown("#### Treatment")
            for treatment in disease['treatment']:
                st.info(f"• {treatment}")
            
            if disease['critical']:
                st.error("⚠️ This is a critical disease. Consult veterinarian immediately!")

def show_breeding_manager():
    st.markdown("### Breeding Manager")
    user = st.session_state.user_data
    
    tab1, tab2 = st.tabs(["Record Breeding", "Breeding Calendar"])
    
    with tab1:
        conn = sqlite3.connect('buffalomitra.db')
        c = conn.cursor()
        c.execute("""SELECT id, tag_number, name FROM buffalo_inventory 
                     WHERE user_id=? AND status='Active'""", (user['id'],))
        buffaloes = c.fetchall()
        conn.close()
        
        if buffaloes:
            with st.form("record_breeding"):
                buffalo_options = {f"{b[1]} - {b[2]}": b[0] for b in buffaloes}
                selected = st.selectbox("Select Buffalo", list(buffalo_options.keys()))
                buffalo_id = buffalo_options[selected]
                
                col1, col2 = st.columns(2)
                with col1:
                    breeding_date = st.date_input("Breeding Date", value=datetime.now())
                    breeding_type = st.selectbox("Breeding Type", ["Natural", "AI"])
                    bull_details = st.text_input("Bull Details/Breed")
                with col2:
                    expected_calving = breeding_date + timedelta(days=310)
                    st.date_input("Expected Calving Date", value=expected_calving, disabled=True)
                    notes = st.text_area("Notes")
                
                submitted = st.form_submit_button("Record Breeding", use_container_width=True, type="primary")
                
                if submitted:
                    conn = sqlite3.connect('buffalomitra.db')
                    c = conn.cursor()
                    c.execute("""INSERT INTO breeding_records 
                                (user_id, buffalo_id, breeding_date, breeding_type, 
                                 bull_details, expected_calving_date, pregnancy_status, notes)
                                VALUES (?, ?, ?, ?, ?, ?, 'Bred', ?)""",
                             (user['id'], buffalo_id, breeding_date, breeding_type,
                              bull_details, expected_calving, notes))
                    conn.commit()
                    conn.close()
                    st.success("Breeding recorded!")
                    st.rerun()
        else:
            st.warning("No buffaloes found in inventory!")
    
    with tab2:
        conn = sqlite3.connect('buffalomitra.db')
        df = pd.read_sql_query(
            """SELECT br.breeding_date, bi.tag_number, bi.name, br.breeding_type,
               br.expected_calving_date, br.pregnancy_status
               FROM breeding_records br
               JOIN buffalo_inventory bi ON br.buffalo_id = bi.id
               WHERE br.user_id=? AND br.pregnancy_status IN ('Bred', 'Pregnant')
               ORDER BY br.expected_calving_date""",
            conn, params=(user['id'],))
        conn.close()
        
        if not df.empty:
            st.dataframe(df, use_container_width=True)

def show_health_records():
    st.markdown("### Health Records")
    user = st.session_state.user_data
    
    tab1, tab2 = st.tabs(["Add Record", "View History"])
    
    with tab1:
        conn = sqlite3.connect('buffalomitra.db')
        c = conn.cursor()
        c.execute("""SELECT id, tag_number, name FROM buffalo_inventory 
                     WHERE user_id=? AND status='Active'""", (user['id'],))
        buffaloes = c.fetchall()
        conn.close()
        
        if buffaloes:
            with st.form("health_record"):
                buffalo_options = {f"{b[1]} - {b[2]}": b[0] for b in buffaloes}
                selected = st.selectbox("Select Buffalo", list(buffalo_options.keys()))
                buffalo_id = buffalo_options[selected]
                
                col1, col2 = st.columns(2)
                with col1:
                    date = st.date_input("Date", value=datetime.now())
                    record_type = st.selectbox("Type", ["Vaccination", "Treatment", "Checkup", "Deworming"])
                    disease_name = st.text_input("Disease/Condition")
                    symptoms = st.text_area("Symptoms")
                with col2:
                    treatment = st.text_area("Treatment Given")
                    medicine = st.text_input("Medicine")
                    veterinarian = st.text_input("Veterinarian")
                    cost = st.number_input("Cost (₹)", min_value=0, value=0)
                
                submitted = st.form_submit_button("Save Health Record", use_container_width=True, type="primary")
                
                if submitted:
                    conn = sqlite3.connect('buffalomitra.db')
                    c = conn.cursor()
                    c.execute("""INSERT INTO health_records 
                                (user_id, buffalo_id, date, record_type, disease_name, 
                                 symptoms, treatment, medicine, veterinarian, cost)
                                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                             (user['id'], buffalo_id, date, record_type, disease_name,
                              symptoms, treatment, medicine, veterinarian, cost))
                    conn.commit()
                    conn.close()
                    st.success("Health record saved!")
                    st.rerun()
        else:
            st.warning("No buffaloes found!")
    
    with tab2:
        conn = sqlite3.connect('buffalomitra.db')
        df = pd.read_sql_query(
            """SELECT hr.date, bi.tag_number, bi.name, hr.record_type, 
               hr.disease_name, hr.treatment, hr.cost
               FROM health_records hr
               JOIN buffalo_inventory bi ON hr.buffalo_id = bi.id
               WHERE hr.user_id=? 
               ORDER BY hr.date DESC""",
            conn, params=(user['id'],))
        conn.close()
        
        if not df.empty:
            st.dataframe(df, use_container_width=True)
            st.metric("Total Health Expense", f"₹{df['cost'].sum():,.0f}")

def show_feed_management():
    st.markdown("### Feed Management Guide")
    
    st.markdown("### Feeding Schedule")
    
    for feed_type, feed_info in FEED_DATABASE.items():
        with st.expander(f"📦 {feed_type.replace('_', ' ')}"):
            st.write(f"**Items:** {', '.join(feed_info['items'])}")
            st.write(f"**Daily Requirement:** {feed_info['requirement_kg_per_day']} kg")
            st.write(f"**Cost:** {feed_info['cost_per_kg']}")
            st.write(f"**Benefits:** {feed_info['benefits']}")
            
            if 'formula' in feed_info:
                st.info(f"**Formula:** {feed_info['formula']}")
    
    st.markdown("### Feed Calculator")
    num_buffaloes = st.number_input("Number of Buffaloes", min_value=1, value=1)
    avg_milk_yield = st.number_input("Average Milk Yield per Buffalo (L/day)", min_value=0.0, value=10.0)
    
    if st.button("Calculate Feed Requirement", type="primary"):
        green_fodder = 30 * num_buffaloes
        dry_fodder = 10 * num_buffaloes
        concentrate = (avg_milk_yield / 2.5) * num_buffaloes
        mineral = 0.075 * num_buffaloes
        
        st.markdown("### Daily Feed Requirement")
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.metric("Green Fodder", f"{green_fodder:.0f} kg")
        with col2:
            st.metric("Dry Fodder", f"{dry_fodder:.0f} kg")
        with col3:
            st.metric("Concentrate", f"{concentrate:.1f} kg")
        with col4:
            st.metric("Mineral Mix", f"{mineral:.2f} kg")
        
        daily_cost = (green_fodder * 3) + (dry_fodder * 4) + (concentrate * 25) + (mineral * 50)
        monthly_cost = daily_cost * 30
        
        st.success(f"**Daily Feed Cost:** ₹{daily_cost:,.0f}")
        st.info(f"**Monthly Feed Cost:** ₹{monthly_cost:,.0f}")

def show_milk_price_tracker():
    st.markdown("### Milk Price Tracker")
    
    st.markdown("### Current Market Rates (Maharashtra)")
    
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("Dairy Company", "₹55-65/L")
        st.caption("Based on fat %")
    with col2:
        st.metric("Local Market", "₹70-85/L")
        st.caption("Direct to consumer")
    with col3:
        st.metric("Cooperative", "₹58-68/L")
        st.caption("Based on SNF & fat")
    
    st.markdown("### Price Calculator")
    fat_percent = st.slider("Fat %", 3.0, 12.0, 7.5, 0.1)
    snf_percent = st.slider("SNF %", 7.0, 11.0, 9.0, 0.1)
    
    base_price = 40
    fat_rate = 8
    snf_rate = 6
    
    calculated_price = base_price + (fat_percent * fat_rate) + (snf_percent * snf_rate)
    
    st.success(f"**Estimated Price:** ₹{calculated_price:.2f} per liter")

def show_financial_manager():
    st.markdown("### Financial Manager")
    user = st.session_state.user_data
    
    tab1, tab2 = st.tabs(["Add Transaction", "Financial Summary"])
    
    with tab1:
        with st.form("add_transaction"):
            col1, col2 = st.columns(2)
            with col1:
                transaction_type = st.selectbox("Type", ["Income", "Expense"])
                category = st.selectbox("Category", 
                    ["Milk Sale", "Buffalo Sale", "Feed", "Medicine", "Veterinary", 
                     "Equipment", "Labor", "Other"])
                amount = st.number_input("Amount (₹)", min_value=0, value=1000)
            with col2:
                date = st.date_input("Date", value=datetime.now())
                description = st.text_area("Description")
            
            submitted = st.form_submit_button("Add", use_container_width=True, type="primary")
            
            if submitted:
                conn = sqlite3.connect('buffalomitra.db')
                c = conn.cursor()
                c.execute("""INSERT INTO financial_records 
                            (user_id, date, category, transaction_type, amount, description)
                            VALUES (?, ?, ?, ?, ?, ?)""",
                         (user['id'], date, category, transaction_type, amount, description))
                conn.commit()
                conn.close()
                st.success("Transaction added!")
                st.rerun()
    
    with tab2:
        conn = sqlite3.connect('buffalomitra.db')
        c = conn.cursor()
        
        c.execute("""SELECT transaction_type, SUM(amount) FROM financial_records 
                     WHERE user_id=? GROUP BY transaction_type""", (user['id'],))
        summary = dict(c.fetchall())
        conn.close()
        
        total_income = summary.get('Income', 0)
        total_expense = summary.get('Expense', 0)
        net_profit = total_income - total_expense
        
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("Total Income", f"₹{total_income:,.0f}")
        with col2:
            st.metric("Total Expenses", f"₹{total_expense:,.0f}")
        with col3:
            st.metric("Net Profit", f"₹{net_profit:,.0f}")

def show_profit_calculator():
    st.markdown("### Profit Calculator")
    
    st.markdown("### Income")
    num_buffaloes = st.number_input("Number of Lactating Buffaloes", min_value=1, value=5)
    avg_milk = st.number_input("Average Milk per Buffalo (L/day)", min_value=0.0, value=10.0)
    milk_price = st.number_input("Milk Price (₹/L)", min_value=0, value=60)
    
    daily_milk = num_buffaloes * avg_milk
    daily_income = daily_milk * milk_price
    monthly_income = daily_income * 30
    
    st.markdown("### Expenses")
    feed_cost_per_buffalo = st.number_input("Feed Cost per Buffalo (₹/day)", min_value=0, value=250)
    medicine_monthly = st.number_input("Medicine & Veterinary (₹/month)", min_value=0, value=3000)
    labor_monthly = st.number_input("Labor Cost (₹/month)", min_value=0, value=10000)
    other_monthly = st.number_input("Other Expenses (₹/month)", min_value=0, value=5000)
    
    monthly_feed = feed_cost_per_buffalo * num_buffaloes * 30
    monthly_expense = monthly_feed + medicine_monthly + labor_monthly + other_monthly
    
    monthly_profit = monthly_income - monthly_expense
    annual_profit = monthly_profit * 12
    roi = (annual_profit / (monthly_expense * 12)) * 100 if monthly_expense > 0 else 0
    
    st.markdown("---")
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("Monthly Income", f"₹{monthly_income:,.0f}")
    with col2:
        st.metric("Monthly Expense", f"₹{monthly_expense:,.0f}")
    with col3:
        st.metric("Monthly Profit", f"₹{monthly_profit:,.0f}")
    
    col1, col2 = st.columns(2)
    with col1:
        st.metric("Annual Profit", f"₹{annual_profit:,.0f}")
    with col2:
        st.metric("ROI", f"{roi:.1f}%")

def show_government_schemes():
    st.markdown("### Government Schemes")
    
    for scheme_id, scheme in GOVERNMENT_SCHEMES.items():
        with st.expander(f"📋 {scheme['name']}"):
            st.markdown(f"**Benefit:** {scheme['benefit']}")
            st.markdown(f"**Eligibility:** {scheme['eligibility']}")
            st.markdown(f"**How to Apply:** {scheme['how_to_apply']}")
            st.markdown(f"**Contact:** {scheme['contact']}")

def show_buyer_connect():
    st.markdown("### Buyer Connect")
    user = st.session_state.user_data
    
    st.markdown("### Register Milk Buyer")
    with st.form("register_buyer"):
        col1, col2 = st.columns(2)
        with col1:
            buyer_name = st.text_input("Buyer Name")
            contact = st.text_input("Contact Number")
        with col2:
            price_per_liter = st.number_input("Price per Liter (₹)", min_value=0, value=60)
            payment_terms = st.text_input("Payment Terms", value="Weekly")
        
        submitted = st.form_submit_button("Register", use_container_width=True, type="primary")
        
        if submitted and buyer_name and contact:
            conn = sqlite3.connect('buffalomitra.db')
            c = conn.cursor()
            c.execute("""INSERT INTO milk_buyers 
                        (user_id, buyer_name, contact, price_per_liter, payment_terms, active)
                        VALUES (?, ?, ?, ?, ?, 1)""",
                     (user['id'], buyer_name, contact, price_per_liter, payment_terms))
            conn.commit()
            conn.close()
            st.success("Buyer registered!")
            st.rerun()

def show_insurance_calculator():
    st.markdown("### Livestock Insurance Calculator")
    
    num_buffaloes = st.number_input("Number of Buffaloes to Insure", min_value=1, value=5)
    avg_value = st.number_input("Average Value per Buffalo (₹)", min_value=10000, value=100000)
    
    total_sum_insured = num_buffaloes * avg_value
    premium_rate = 3.0
    annual_premium = total_sum_insured * (premium_rate / 100)
    govt_subsidy = annual_premium * 0.5
    farmer_premium = annual_premium - govt_subsidy
    
    st.markdown("### Insurance Details")
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("Total Sum Insured", f"₹{total_sum_insured:,.0f}")
    with col2:
        st.metric("Your Premium", f"₹{farmer_premium:,.0f}")
    with col3:
        st.metric("Govt Subsidy", f"₹{govt_subsidy:,.0f}")

# ====== NEW FEATURES ======

def show_alerts_reminders():
    st.markdown("### Alerts & Reminders")
    user = st.session_state.user_data
    
    alerts = generate_alerts(user['id'])
    
    if alerts:
        high = [a for a in alerts if a['priority'] == 'high']
        medium = [a for a in alerts if a['priority'] == 'medium']
        
        if high:
            st.markdown("### 🔴 High Priority")
            for alert in high:
                st.markdown(f'<div class="alert-card">{alert["message"]}</div>', unsafe_allow_html=True)
        
        if medium:
            st.markdown("### 🟡 Medium Priority")
            for alert in medium:
                st.markdown(f'<div class="warning-card">{alert["message"]}</div>', unsafe_allow_html=True)
    else:
        st.success("No pending alerts!")

def show_calf_management():
    st.markdown("### Calf Management")
    user = st.session_state.user_data
    
    tab1, tab2 = st.tabs(["Add Calf", "View Calves"])
    
    with tab1:
        conn = sqlite3.connect('buffalomitra.db')
        c = conn.cursor()
        c.execute("""SELECT id, tag_number, name FROM buffalo_inventory 
                     WHERE user_id=? AND status='Active'""", (user['id'],))
        buffaloes = c.fetchall()
        conn.close()
        
        if buffaloes:
            with st.form("add_calf"):
                buffalo_options = {f"{b[1]} - {b[2]}": b[0] for b in buffaloes}
                selected = st.selectbox("Mother Buffalo", list(buffalo_options.keys()))
                mother_id = buffalo_options[selected]
                
                col1, col2 = st.columns(2)
                with col1:
                    tag_number = st.text_input("Calf Tag Number*")
                    name = st.text_input("Name")
                    dob = st.date_input("Date of Birth", value=datetime.now())
                    gender = st.selectbox("Gender", ["Male", "Female"])
                with col2:
                    birth_weight = st.number_input("Birth Weight (kg)", min_value=0.0, value=25.0)
                    breed = st.selectbox("Breed", list(BUFFALO_BREEDS.keys()))
                    notes = st.text_area("Notes")
                
                submitted = st.form_submit_button("Add Calf", use_container_width=True, type="primary")
                
                if submitted and tag_number:
                    conn = sqlite3.connect('buffalomitra.db')
                    c = conn.cursor()
                    try:
                        c.execute("""INSERT INTO calf_records 
                                    (user_id, mother_buffalo_id, tag_number, name, date_of_birth, 
                                     gender, birth_weight, breed, status, notes)
                                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, 'Active', ?)""",
                                 (user['id'], mother_id, tag_number, name, dob, gender, 
                                  birth_weight, breed, notes))
                        conn.commit()
                        st.success("Calf added successfully!")
                        st.rerun()
                    except sqlite3.IntegrityError:
                        st.error("Tag number already exists!")
                    finally:
                        conn.close()
        else:
            st.warning("No buffaloes found!")
    
    with tab2:
        conn = sqlite3.connect('buffalomitra.db')
        df = pd.read_sql_query(
            """SELECT c.tag_number, c.name, c.gender, c.date_of_birth, c.birth_weight,
               c.breed, b.name as mother_name, c.status
               FROM calf_records c
               JOIN buffalo_inventory b ON c.mother_buffalo_id = b.id
               WHERE c.user_id=?
               ORDER BY c.date_of_birth DESC""",
            conn, params=(user['id'],))
        conn.close()
        
        if not df.empty:
            st.dataframe(df, use_container_width=True)
            
            col1, col2 = st.columns(2)
            with col1:
                st.metric("Total Calves", len(df))
            with col2:
                active = len(df[df['status'] == 'Active'])
                st.metric("Active Calves", active)
        else:
            st.info("No calves recorded yet")

def show_heat_detection():
    st.markdown("### Heat Detection Tracker")
    user = st.session_state.user_data
    
    tab1, tab2 = st.tabs(["Record Heat", "Heat History"])
    
    with tab1:
        conn = sqlite3.connect('buffalomitra.db')
        c = conn.cursor()
        c.execute("""SELECT id, tag_number, name FROM buffalo_inventory 
                     WHERE user_id=? AND status='Active'""", (user['id'],))
        buffaloes = c.fetchall()
        conn.close()
        
        if buffaloes:
            with st.form("record_heat"):
                buffalo_options = {f"{b[1]} - {b[2]}": b[0] for b in buffaloes}
                selected = st.selectbox("Select Buffalo", list(buffalo_options.keys()))
                buffalo_id = buffalo_options[selected]
                
                col1, col2 = st.columns(2)
                with col1:
                    heat_date = st.date_input("Heat Date", value=datetime.now())
                    heat_intensity = st.selectbox("Heat Intensity", ["Mild", "Moderate", "Strong"])
                with col2:
                    bred = st.checkbox("Was Bred?")
                    notes = st.text_area("Notes")
                
                submitted = st.form_submit_button("Record Heat", use_container_width=True, type="primary")
                
                if submitted:
                    conn = sqlite3.connect('buffalomitra.db')
                    c = conn.cursor()
                    c.execute("""INSERT INTO heat_detection 
                                (user_id, buffalo_id, heat_date, heat_intensity, bred, notes)
                                VALUES (?, ?, ?, ?, ?, ?)""",
                             (user['id'], buffalo_id, heat_date, heat_intensity, bred, notes))
                    conn.commit()
                    conn.close()
                    st.success("Heat recorded!")
                    st.rerun()
        else:
            st.warning("No buffaloes found!")
    
    with tab2:
        conn = sqlite3.connect('buffalomitra.db')
        df = pd.read_sql_query(
            """SELECT h.heat_date, b.tag_number, b.name, h.heat_intensity, h.bred
               FROM heat_detection h
               JOIN buffalo_inventory b ON h.buffalo_id = b.id
               WHERE h.user_id=?
               ORDER BY h.heat_date DESC LIMIT 50""",
            conn, params=(user['id'],))
        conn.close()
        
        if not df.empty:
            st.dataframe(df, use_container_width=True)
            
            st.info("**Note:** Heat cycles typically occur every 18-24 days. Monitor regularly for optimal breeding!")

def show_vaccination_schedule():
    st.markdown("### Vaccination Schedule")
    user = st.session_state.user_data
    
    tab1, tab2, tab3 = st.tabs(["Record Vaccination", "Upcoming Due", "History"])
    
    with tab1:
        conn = sqlite3.connect('buffalomitra.db')
        c = conn.cursor()
        c.execute("""SELECT id, tag_number, name FROM buffalo_inventory 
                     WHERE user_id=? AND status='Active'""", (user['id'],))
        buffaloes = c.fetchall()
        conn.close()
        
        if buffaloes:
            with st.form("record_vaccination"):
                buffalo_options = {f"{b[1]} - {b[2]}": b[0] for b in buffaloes}
                selected = st.selectbox("Select Buffalo", list(buffalo_options.keys()))
                buffalo_id = buffalo_options[selected]
                
                col1, col2 = st.columns(2)
                with col1:
                    vacc_type = st.selectbox("Vaccination Type", list(VACCINATION_SCHEDULE.keys()))
                    date = st.date_input("Date", value=datetime.now())
                    veterinarian = st.text_input("Veterinarian")
                with col2:
                    frequency = VACCINATION_SCHEDULE[vacc_type]['frequency_months']
                    next_due = date + timedelta(days=frequency * 30)
                    st.date_input("Next Due Date", value=next_due, disabled=True)
                    cost = st.number_input("Cost (₹)", min_value=0, value=100)
                    batch_number = st.text_input("Batch Number")
                
                submitted = st.form_submit_button("Record Vaccination", use_container_width=True, type="primary")
                
                if submitted:
                    conn = sqlite3.connect('buffalomitra.db')
                    c = conn.cursor()
                    c.execute("""INSERT INTO vaccination_records 
                                (user_id, buffalo_id, vaccination_type, date, next_due_date, 
                                 veterinarian, cost, batch_number)
                                VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
                             (user['id'], buffalo_id, vacc_type, date, next_due, 
                              veterinarian, cost, batch_number))
                    conn.commit()
                    conn.close()
                    st.success("Vaccination recorded!")
                    st.rerun()
        else:
            st.warning("No buffaloes found!")
    
    with tab2:
        st.markdown("### Upcoming Vaccinations")
        conn = sqlite3.connect('buffalomitra.db')
        df = pd.read_sql_query(
            """SELECT v.next_due_date, b.tag_number, b.name, v.vaccination_type
               FROM vaccination_records v
               JOIN buffalo_inventory b ON v.buffalo_id = b.id
               WHERE v.user_id=? AND v.next_due_date >= date('now')
               ORDER BY v.next_due_date LIMIT 20""",
            conn, params=(user['id'],))
        conn.close()
        
        if not df.empty:
            st.dataframe(df, use_container_width=True)
        else:
            st.info("No upcoming vaccinations")
    
    with tab3:
        conn = sqlite3.connect('buffalomitra.db')
        df = pd.read_sql_query(
            """SELECT v.date, b.tag_number, b.name, v.vaccination_type, 
               v.veterinarian, v.cost
               FROM vaccination_records v
               JOIN buffalo_inventory b ON v.buffalo_id = b.id
               WHERE v.user_id=?
               ORDER BY v.date DESC""",
            conn, params=(user['id'],))
        conn.close()
        
        if not df.empty:
            st.dataframe(df, use_container_width=True)
            st.metric("Total Vaccination Cost", f"₹{df['cost'].sum():,.0f}")

def show_feed_inventory():
    st.markdown("### Feed Inventory Management")
    user = st.session_state.user_data
    
    tab1, tab2 = st.tabs(["Add/Update Stock", "Current Inventory"])
    
    with tab1:
        with st.form("manage_feed_stock"):
            col1, col2 = st.columns(2)
            with col1:
                feed_name = st.text_input("Feed Name*")
                feed_type = st.selectbox("Feed Type", ["Green Fodder", "Dry Fodder", "Concentrate", "Mineral Mix", "Other"])
                current_stock = st.number_input("Current Stock (kg)", min_value=0.0, value=100.0)
                reorder_level = st.number_input("Reorder Level (kg)", min_value=0.0, value=50.0)
            with col2:
                last_purchase_date = st.date_input("Last Purchase Date")
                last_purchase_quantity = st.number_input("Purchase Quantity (kg)", min_value=0.0, value=100.0)
                last_purchase_cost = st.number_input("Purchase Cost (₹)", min_value=0, value=1000)
                supplier = st.text_input("Supplier")
            
            submitted = st.form_submit_button("Save", use_container_width=True, type="primary")
            
            if submitted and feed_name:
                conn = sqlite3.connect('buffalomitra.db')
                c = conn.cursor()
                c.execute("""INSERT OR REPLACE INTO feed_inventory 
                            (user_id, feed_name, feed_type, current_stock_kg, reorder_level_kg,
                             last_purchase_date, last_purchase_quantity, last_purchase_cost, supplier)
                            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                         (user['id'], feed_name, feed_type, current_stock, reorder_level,
                          last_purchase_date, last_purchase_quantity, last_purchase_cost, supplier))
                conn.commit()
                conn.close()
                st.success("Feed stock updated!")
                st.rerun()
    
    with tab2:
        conn = sqlite3.connect('buffalomitra.db')
        df = pd.read_sql_query(
            """SELECT feed_name, feed_type, current_stock_kg, reorder_level_kg,
               last_purchase_date, supplier
               FROM feed_inventory
               WHERE user_id=?
               ORDER BY feed_type, feed_name""",
            conn, params=(user['id'],))
        conn.close()
        
        if not df.empty:
            st.dataframe(df, use_container_width=True)
            
            low_stock = df[df['current_stock_kg'] <= df['reorder_level_kg']]
            if not low_stock.empty:
                st.warning(f"⚠️ {len(low_stock)} items are low on stock!")
                st.dataframe(low_stock[['feed_name', 'current_stock_kg', 'reorder_level_kg']])
        else:
            st.info("No feed inventory records yet")

def show_labor_management():
    st.markdown("### Labor Management")
    user = st.session_state.user_data
    
    tab1, tab2 = st.tabs(["Add Worker", "View Workers"])
    
    with tab1:
        with st.form("add_worker"):
            col1, col2 = st.columns(2)
            with col1:
                worker_name = st.text_input("Worker Name*")
                contact = st.text_input("Contact Number")
                role = st.selectbox("Role", ["Farm Manager", "Milker", "Cleaner", "Helper", "Other"])
            with col2:
                monthly_salary = st.number_input("Monthly Salary (₹)", min_value=0, value=10000)
                join_date = st.date_input("Joining Date")
            
            submitted = st.form_submit_button("Add Worker", use_container_width=True, type="primary")
            
            if submitted and worker_name:
                conn = sqlite3.connect('buffalomitra.db')
                c = conn.cursor()
                c.execute("""INSERT INTO labor_records 
                            (user_id, worker_name, contact, role, monthly_salary, join_date, active)
                            VALUES (?, ?, ?, ?, ?, ?, 1)""",
                         (user['id'], worker_name, contact, role, monthly_salary, join_date))
                conn.commit()
                conn.close()
                st.success("Worker added!")
                st.rerun()
    
    with tab2:
        conn = sqlite3.connect('buffalomitra.db')
        df = pd.read_sql_query(
            """SELECT worker_name, contact, role, monthly_salary, join_date, active
               FROM labor_records
               WHERE user_id=?
               ORDER BY active DESC, worker_name""",
            conn, params=(user['id'],))
        conn.close()
        
        if not df.empty:
            st.dataframe(df, use_container_width=True)
            
            active_workers = df[df['active'] == 1]
            if not active_workers.empty:
                total_salary = active_workers['monthly_salary'].sum()
                st.metric("Total Monthly Labor Cost", f"₹{total_salary:,.0f}")

def show_advanced_analytics():
    st.markdown("### Advanced Analytics")
    user = st.session_state.user_data
    
    conn = sqlite3.connect('buffalomitra.db')
    
    # Buffalo-wise production
    st.markdown("### Buffalo-wise Performance")
    df_buffalo = pd.read_sql_query(
        """SELECT b.tag_number, b.name, b.breed,
           AVG(m.total_yield) as avg_yield,
           AVG(m.fat_percentage) as avg_fat,
           COUNT(m.id) as records
           FROM buffalo_inventory b
           LEFT JOIN milk_production m ON b.id = m.buffalo_id
           WHERE b.user_id=? AND b.status='Active' AND m.date >= date('now', '-90 days')
           GROUP BY b.id
           HAVING records > 0
           ORDER BY avg_yield DESC""",
        conn, params=(user['id'],))
    
    if not df_buffalo.empty:
        fig = px.bar(df_buffalo, x='tag_number', y='avg_yield', 
                    title='Average Daily Milk Yield by Buffalo (Last 90 Days)',
                    labels={'avg_yield': 'Avg Milk (L)', 'tag_number': 'Buffalo Tag'},
                    color='avg_fat', color_continuous_scale='Viridis')
        st.plotly_chart(fig, use_container_width=True)
        
        st.dataframe(df_buffalo, use_container_width=True)
    
    # Breed-wise comparison
    st.markdown("### Breed-wise Comparison")
    df_breed = pd.read_sql_query(
        """SELECT b.breed,
           COUNT(DISTINCT b.id) as count,
           AVG(m.total_yield) as avg_yield,
           AVG(m.fat_percentage) as avg_fat
           FROM buffalo_inventory b
           LEFT JOIN milk_production m ON b.id = m.buffalo_id
           WHERE b.user_id=? AND m.date >= date('now', '-90 days')
           GROUP BY b.breed""",
        conn, params=(user['id'],))
    
    if not df_breed.empty:
        col1, col2 = st.columns(2)
        with col1:
            fig1 = px.pie(df_breed, values='count', names='breed', 
                         title='Buffalo Distribution by Breed')
            st.plotly_chart(fig1, use_container_width=True)
        with col2:
            fig2 = px.bar(df_breed, x='breed', y='avg_yield',
                         title='Average Yield by Breed')
            st.plotly_chart(fig2, use_container_width=True)
    
    # Monthly trends
    st.markdown("### Monthly Production Trends")
    df_monthly = pd.read_sql_query(
        """SELECT strftime('%Y-%m', date) as month,
           SUM(total_yield) as total_milk,
           AVG(fat_percentage) as avg_fat,
           COUNT(DISTINCT buffalo_id) as active_buffaloes
           FROM milk_production
           WHERE user_id=? AND date >= date('now', '-12 months')
           GROUP BY month
           ORDER BY month""",
        conn, params=(user['id'],))
    
    if not df_monthly.empty:
        fig = go.Figure()
        fig.add_trace(go.Bar(x=df_monthly['month'], y=df_monthly['total_milk'],
                            name='Total Milk', yaxis='y'))
        fig.add_trace(go.Scatter(x=df_monthly['month'], y=df_monthly['avg_fat'],
                                name='Avg Fat %', yaxis='y2', mode='lines+markers'))
        
        fig.update_layout(
            title='Monthly Production & Fat % Trends',
            xaxis=dict(title='Month'),
            yaxis=dict(title='Total Milk (L)'),
            yaxis2=dict(title='Fat %', overlaying='y', side='right')
        )
        st.plotly_chart(fig, use_container_width=True)
    
    conn.close()

def show_reports_generator():
    st.markdown("### Reports Generator")
    user = st.session_state.user_data
    
    report_type = st.selectbox("Select Report Type", [
        "Monthly Production Report",
        "Financial Summary Report",
        "Buffalo Health Report",
        "Breeding Performance Report"
    ])
    
    col1, col2 = st.columns(2)
    with col1:
        start_date = st.date_input("Start Date", value=datetime.now().date() - timedelta(days=30))
    with col2:
        end_date = st.date_input("End Date", value=datetime.now().date())
    
    if st.button("Generate Report", type="primary", use_container_width=True):
        conn = sqlite3.connect('buffalomitra.db')
        
        if report_type == "Monthly Production Report":
            st.markdown("### Monthly Production Report")
            st.markdown(f"**Period:** {start_date} to {end_date}")
            
            df = pd.read_sql_query(
                """SELECT date, 
                   SUM(total_yield) as daily_milk,
                   AVG(fat_percentage) as avg_fat,
                   AVG(price_per_liter) as avg_price
                   FROM milk_production
                   WHERE user_id=? AND date BETWEEN ? AND ?
                   GROUP BY date
                   ORDER BY date""",
                conn, params=(user['id'], start_date, end_date))
            
            if not df.empty:
                total_milk = df['daily_milk'].sum()
                avg_daily = df['daily_milk'].mean()
                total_revenue = (df['daily_milk'] * df['avg_price']).sum()
                
                col1, col2, col3 = st.columns(3)
                with col1:
                    st.metric("Total Milk Production", f"{total_milk:.1f} L")
                with col2:
                    st.metric("Average Daily Production", f"{avg_daily:.1f} L")
                with col3:
                    st.metric("Total Revenue", f"₹{total_revenue:,.0f}")
                
                st.dataframe(df, use_container_width=True)
                
                # Download option
                csv = df.to_csv(index=False).encode('utf-8')
                st.download_button(
                    "Download Report as CSV",
                    csv,
                    "production_report.csv",
                    "text/csv",
                    key='download-csv'
                )
        
        elif report_type == "Financial Summary Report":
            st.markdown("### Financial Summary Report")
            st.markdown(f"**Period:** {start_date} to {end_date}")
            
            df = pd.read_sql_query(
                """SELECT category, transaction_type, SUM(amount) as total
                   FROM financial_records
                   WHERE user_id=? AND date BETWEEN ? AND ?
                   GROUP BY category, transaction_type
                   ORDER BY transaction_type, total DESC""",
                conn, params=(user['id'], start_date, end_date))
            
            if not df.empty:
                income = df[df['transaction_type'] == 'Income']['total'].sum()
                expense = df[df['transaction_type'] == 'Expense']['total'].sum()
                profit = income - expense
                
                col1, col2, col3 = st.columns(3)
                with col1:
                    st.metric("Total Income", f"₹{income:,.0f}")
                with col2:
                    st.metric("Total Expense", f"₹{expense:,.0f}")
                with col3:
                    st.metric("Net Profit", f"₹{profit:,.0f}")
                
                st.dataframe(df, use_container_width=True)
        
        elif report_type == "Buffalo Health Report":
            st.markdown("### Buffalo Health Report")
            st.markdown(f"**Period:** {start_date} to {end_date}")
            
            df = pd.read_sql_query(
                """SELECT b.tag_number, b.name, h.date, h.record_type, 
                   h.disease_name, h.treatment, h.cost
                   FROM health_records h
                   JOIN buffalo_inventory b ON h.buffalo_id = b.id
                   WHERE h.user_id=? AND h.date BETWEEN ? AND ?
                   ORDER BY h.date DESC""",
                conn, params=(user['id'], start_date, end_date))
            
            if not df.empty:
                st.dataframe(df, use_container_width=True)
                st.metric("Total Health Expenditure", f"₹{df['cost'].sum():,.0f}")
        
        elif report_type == "Breeding Performance Report":
            st.markdown("### Breeding Performance Report")
            
            df = pd.read_sql_query(
                """SELECT b.tag_number, b.name, br.breeding_date, br.breeding_type,
                   br.expected_calving_date, br.pregnancy_status
                   FROM breeding_records br
                   JOIN buffalo_inventory b ON br.buffalo_id = b.id
                   WHERE br.user_id=? AND br.breeding_date BETWEEN ? AND ?
                   ORDER BY br.breeding_date DESC""",
                conn, params=(user['id'], start_date, end_date))
            
            if not df.empty:
                st.dataframe(df, use_container_width=True)
                
                total_breeding = len(df)
                ai_count = len(df[df['breeding_type'] == 'AI'])
                natural_count = len(df[df['breeding_type'] == 'Natural'])
                
                col1, col2, col3 = st.columns(3)
                with col1:
                    st.metric("Total Breedings", total_breeding)
                with col2:
                    st.metric("AI Breedings", ai_count)
                with col3:
                    st.metric("Natural Breedings", natural_count)
        
        conn.close()

if __name__ == "__main__":
    main()