from flask import Flask, render_template, request, redirect, url_for, jsonify
import pandas as pd
import plotly.graph_objs as go
import plotly.utils
import json
import os
import numpy as np
import psycopg2

app = Flask(__name__)

# SECRET_KEY from environment
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'dev-key-change-in-production')

# DATABASE_URL from environment (Postgres)
DATABASE_URL = os.environ.get('DATABASE_URL')

def get_db_connection():
    conn = psycopg2.connect(DATABASE_URL)
    return conn

def init_db():
    conn = get_db_connection()
    cur = conn.cursor()

    cur.execute('''
        CREATE TABLE IF NOT EXISTS leads (
            id SERIAL PRIMARY KEY,
            date DATE NOT NULL,
            source TEXT NOT NULL,
            lead_count INTEGER NOT NULL,
            cost REAL NOT NULL
        )
    ''')

    cur.execute('''
        CREATE TABLE IF NOT EXISTS conversions (
            id SERIAL PRIMARY KEY,
            date DATE NOT NULL,
            source TEXT NOT NULL,
            conversions INTEGER NOT NULL,
            revenue REAL NOT NULL
        )
    ''')

    conn.commit()
    cur.close()
    conn.close()

def calculate_metrics():
    conn = get_db_connection()
    leads_df = pd.read_sql_query('SELECT * FROM leads', conn)
    conversions_df = pd.read_sql_query('SELECT * FROM conversions', conn)
    conn.close()

    if leads_df.empty and conversions_df.empty:
        return {
            'total_leads': 0,
            'total_conversions': 0,
            'conversion_rate': 0,
            'total_revenue': 0,
            'cac': 0,
            'ltv': 1200,
            'mrr': 0,
            'churn_rate': 5
        }

    total_leads = leads_df['lead_count'].sum()
    total_conversions = conversions_df['conversions'].sum()
    total_revenue = conversions_df['revenue'].sum()
    total_cost = leads_df['cost'].sum()

    conversion_rate = (total_conversions / total_leads * 100) if total_leads > 0 else 0
    cac = total_cost / total_conversions if total_conversions > 0 else 0

    ltv = 1200
    mrr = total_revenue * 0.1
    churn_rate = 5

    return {
        'total_leads': int(total_leads),
        'total_conversions': int(total_conversions),
        'conversion_rate': round(conversion_rate, 2),
        'total_revenue': round(total_revenue, 2),
        'cac': round(cac, 2),
