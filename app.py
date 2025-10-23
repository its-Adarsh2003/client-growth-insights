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
        'ltv': round(ltv, 2),
        'mrr': round(mrr, 2),
        'churn_rate': round(churn_rate, 2)
    }

@app.route('/')
def dashboard():
    conn = get_db_connection()
    metrics = calculate_metrics()

    leads_df = pd.read_sql_query('''
        SELECT date, SUM(lead_count) as leads, SUM(cost) as cost
        FROM leads
        GROUP BY date
        ORDER BY date
    ''', conn)

    conversions_df = pd.read_sql_query('''
        SELECT date, SUM(conversions) as conversions, SUM(revenue) as revenue
        FROM conversions
        GROUP BY date
        ORDER BY date
    ''', conn)

    charts = {}

    if not leads_df.empty and not conversions_df.empty:
        total_leads = leads_df['leads'].sum()
        total_conversions = conversions_df['conversions'].sum()

        fig_funnel = go.Figure(go.Funnel(
            y=['Leads', 'Conversions'],
            x=[total_leads, total_conversions],
            textposition='inside'
        ))
        fig_funnel.update_layout(title='Conversion Funnel', height=400)
        charts['funnel'] = json.dumps(fig_funnel, cls=plotly.utils.PlotlyJSONEncoder)
    else:
        charts['funnel'] = None

    if not conversions_df.empty:
        fig_revenue = go.Figure()
        fig_revenue.add_trace(go.Scatter(
            x=conversions_df['date'],
            y=conversions_df['revenue'].cumsum(),
            mode='lines+markers',
            name='Cumulative Revenue'
        ))
        fig_revenue.update_layout(title='Revenue Growth', height=400)
        charts['revenue'] = json.dumps(fig_revenue, cls=plotly.utils.PlotlyJSONEncoder)
    else:
        charts['revenue'] = None

    source_performance = pd.read_sql_query('''
        SELECT
            l.source,
            SUM(l.lead_count) as leads,
            SUM(COALESCE(c.conversions, 0)) as conversions,
            SUM(l.cost) as cost,
            SUM(COALESCE(c.revenue, 0)) as revenue
        FROM leads l
        LEFT JOIN conversions c ON l.source = c.source AND l.date = c.date
        GROUP BY l.source
        ORDER BY revenue DESC
    ''', conn)

    conn.close()

    return render_template('dashboard.html',
                           metrics=metrics,
                           charts=charts,
                           source_performance=source_performance.to_dict('records') if not source_performance.empty else [])

@app.route('/add_data', methods=['POST'])
def add_data():
    data_type = request.form['data_type']
    date = request.form['date']
    source = request.form['source']

    conn = get_db_connection()
    cur = conn.cursor()

    try:
        if data_type == 'leads':
            lead_count = int(request.form['lead_count'])
            cost = float(request.form['cost'])
            cur.execute('''
                INSERT INTO leads (date, source, lead_count, cost)
                VALUES (%s, %s, %s, %s)
            ''', (date, source, lead_count, cost))

        elif data_type == 'conversions':
            conversions = int(request.form['conversions'])
            revenue = float(request.form['revenue'])
            cur.execute('''
                INSERT INTO conversions (date, source, conversions, revenue)
                VALUES (%s, %s, %s, %s)
            ''', (date, source, conversions, revenue))

        conn.commit()
    except Exception as e:
        conn.rollback()
        return jsonify({'error': str(e)}), 400
    finally:
        cur.close()
        conn.close()

    return redirect(url_for('dashboard'))

@app.route('/api/metrics')
def api_metrics():
    return jsonify(calculate_metrics())

if __name__ == '__main__':
    init_db()

    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute('SELECT COUNT(*) FROM leads')
    leads_count = cur.fetchone()[0]

    if leads_count == 0:
        sample_leads = [
            ('2024-09-01', 'Google Ads', 150, 750),
            ('2024-09-02', 'Facebook', 80, 400),
            ('2024-09-03', 'LinkedIn', 45, 300),
            ('2024-09-04', 'Google Ads', 200, 1000),
            ('2024-09-05', 'Organic', 60, 0),
        ]
        sample_conversions = [
            ('2024-09-01', 'Google Ads', 15, 1500),
            ('2024-09-02', 'Facebook', 8, 800),
            ('2024-09-03', 'LinkedIn', 6, 1200),
            ('2024-09-04', 'Google Ads', 25, 2500),
            ('2024-09-05', 'Organic', 12, 1200),
        ]

        for lead_data in sample_leads:
            cur.execute('INSERT INTO leads (date, source, lead_count, cost) VALUES (%s, %s, %s, %s)', lead_data)

        for conv_data in sample_conversions:
            cur.execute('INSERT INTO conversions (date, source, conversions, revenue) VALUES (%s, %s, %s, %s)', conv_data)

        conn.commit()
    cur.close()
    conn.close()

    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
