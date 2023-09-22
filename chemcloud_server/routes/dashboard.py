# Later in your Python code, you can format the string as follows:
# formatted_dashboard_html = dashboard_html.format(email='your_email_here')

dashboard_html = """
<html>
<head>
    <title>Dashboard</title>
    <link rel="shortcut icon" href="/favicon.ico" type="image/icon">
    <link rel="icon" href="/favicon.ico" type="image/icon">
    <style>
        /* Reset and basic styles */
        body, h1, h3, ul {{
            margin: 0;
            padding: 0;
            font-family: 'Arial', sans-serif;
        }}

        body {{
            background-color: #f4f5f7;
            color: #333;
            font-size: 16px;
            line-height: 1.5;
        }}

        /* Top menu bar */
        .header {{
            background-color: #70C995; /* Darker Green */
            color: #ffffff;
            padding: 15px 20px;
            display: flex;
            justify-content: space-between;
            align-items: center;
        }}

        .header h1 {{
            margin: 0;
            font-size: 24px;
            font-weight: bold;
        }}

        .header a {{
            color: #ffffff;
            transition: color 0.3s ease;
        }}

        .header a:hover {{
            color: #e5e5e5;
        }}

        .container {{
            max-width: 800px;
            margin: 40px auto;
            background-color: #ffffff;
            border-radius: 10px;
            padding: 20px;
            box-shadow: 0 0 15px rgba(0, 0, 0, 0.1);
        }}

        h3 {{
            text-align: center;
            font-size: 20px;
            margin-bottom: 20px;
            color: #70C995; /* Darker Green */
        }}

        ul {{
            list-style-type: none;
        }}

        ul li {{
            margin-bottom: 15px;
            padding-left: 15px;
            position: relative;
        }}

        ul li:before {{
            content: '•';
            position: absolute;
            left: 0;
            color: #333;
        }}

        a {{
            color: #70C995; /* Darker Green */
            text-decoration: none;
            transition: color 0.3s ease;
        }}

        a:hover {{
            color: #258D5E; /* An even darker shade for hover */
        }}

        @media (max-width: 600px) {{
            .container {{
                margin: 20px 10px;
                padding: 15px;
            }}

            h3 {{
                font-size: 18px;
            }}
        }}
    </style>
</head>

<body>
    <div class="header">
        <h1>ChemCloud Dashboard</h1>
        <a href="/users/logout">Logout</a>
    </div>
    <div class="container">
        <h3>Welcome, {email}!</h3>
        <ul>
            <li>Install the <a href="https://pypi.org/project/chemcloud/" target="_blank">python client</a> and get coding!</li>
            <li>Check out the <a href="/docs">interactive docs</a> to learn more about ChemCloud data types.</li>
            <li>If you need to change your password, please logout, then click "Dashboard", then click "Forgot Password".</li>
        </ul>
    </div>
</body>
</html>
"""
