from flask import Flask, render_template, request
import requests
import xml.etree.ElementTree as ET

app = Flask(__name__)

# רשימת מטבעות להצגה (קוד, שם, סמל)
CURRENCIES = [
    {'code': 'USD', 'name': 'דולר אמריקאי', 'symbol': '$'},
    {'code': 'EUR', 'name': 'אירו', 'symbol': '€'},
    {'code': 'GBP', 'name': 'לירה שטרלינג', 'symbol': '£'},
    {'code': 'JPY', 'name': 'ין יפני', 'symbol': '¥'},
    {'code': 'CHF', 'name': 'פרנק שווייצרי', 'symbol': '₣'},
]

def get_exchange_rates():
    """
    שולף שערי מטבעות מה־API.
    מנסה קודם JSON, ואם לא – עובר ל־XML.
    """
    url = "https://www.boi.org.il/currency.xml"
    response = requests.get(url, timeout=8)
    rates = {'ILS': 1.0}
    # ננסה קודם כ־JSON
    try:
        data = response.json()
        for item in data['exchangeRates']:
            code = item['key']
            rate = float(item['currentExchangeRate'])
            unit = int(item['unit'])
            rates[code] = rate / unit
        print("Loaded exchange rates as JSON.")
        return rates
    except Exception:
        pass  # אם נכשל, ננסה XML
    # ננסה כ־XML
    try:
        tree = ET.fromstring(response.content)
        for currency in tree.findall('.//CURRENCY'):
            code = currency.find('CURRENCYCODE').text
            rate = float(currency.find('RATE').text.replace(',', ''))
            unit = int(currency.find('UNIT').text)
            rates[code] = rate / unit
        print("Loaded exchange rates as XML.")
        return rates
    except Exception as e:
        raise Exception(f"לא ניתן היה לשלוף שערי מטבעות: {e}")

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/vat', methods=['GET', 'POST'])
def vat():
    """מחשבון מע״מ (הוספה/הסרה)"""
    result = None
    error = None
    if request.method == 'POST':
        try:
            amount = float(request.form['amount'])
            vat_action = request.form['vat_action']
            if amount <= 0:
                raise ValueError
            if vat_action == 'add':
                result = {'label': "הוספת מע״מ (17%)", 'value': round(amount * 1.17, 2)}
            else:
                result = {'label': "הסרת מע״מ (17%)", 'value': round(amount / 1.17, 2)}
        except Exception:
            error = "אנא הזן סכום תקין."
    return render_template('vat.html', result=result, error=error)

@app.route('/interest', methods=['GET', 'POST'])
def interest():
    """מחשבון ריבית (פשוטה/דריבית)"""
    result = None
    error = None
    if request.method == 'POST':
        try:
            amount = float(request.form['amount'])
            years = int(request.form['years'])
            rate = float(request.form['rate']) / 100
            compound = request.form.get('compound')
            if amount < 0 or years <= 0 or years > 100 or rate < 0 or rate > 100:
                raise ValueError
            if compound:
                final = amount * ((1 + rate) ** years)
                result = {'label': f"ריבית דריבית ({years} שנים, {rate*100:.2f}%)", 'value': round(final, 2)}
            else:
                final = amount * (1 + rate * years)
                result = {'label': f"ריבית פשוטה ({years} שנים, {rate*100:.2f}%)", 'value': round(final, 2)}
        except Exception:
            error = "אנא מלא ערכים תקינים בלבד."
    return render_template('interest.html', result=result, error=error)

@app.route('/payments', methods=['GET', 'POST'])
def payments():
    result = None
    error = None
    if request.method == 'POST':
        try:
            amount = float(request.form.get('total_amount', '').strip())
            payments = int(request.form.get('payments', '').strip())
            payment_rate = float(request.form.get('rate', '').strip())


            amount = float(amount)
            payments = int(payments)
            payment_rate = float(payment_rate)

            # ולידציה: מספר תשלומים בין 1 ל־1000, ריבית עד 999.999, סכום > 0
            if amount <= 0 or payments < 1 or payments > 1000 or payment_rate < 0 or payment_rate > 999.999:
                raise ValueError

            total = amount * (1 + payment_rate / 100)
            per_payment = total / payments

            result = {
                'label': f'לוח סילוקין של {payments} תשלומים' + (f', עם ריבית/עמלה {payment_rate:.2f}%' if payment_rate > 0 else ''),
                'value': round(per_payment, 2),
                'total': f"{total:,.2f}"
            }
        except Exception:
            error = "אנא הזן ערכים תקינים בלבד."
    return render_template('payments.html', result=result, error=error)

@app.route('/currency', methods=['GET', 'POST'])
def currency():
    """מחשבון המרת מטבעות"""
    result = None
    error = None
    selected_code = 'USD'
    rates = {}
    try:
        rates = get_exchange_rates()
    except Exception as e:
        error = f"לא ניתן היה לשלוף שערים מבנק ישראל: {e}"

    valid_currencies = [c for c in CURRENCIES if c['code'] in rates]

    if request.method == 'POST' and not error:
        try:
            amount = float(request.form['amount'])
            selected_code = request.form['currency']
            if amount < 0 or selected_code not in rates:
                raise ValueError
            curr = next((c for c in valid_currencies if c['code'] == selected_code), None)
            value = round(amount / rates[selected_code], 2)
            if curr:
                result = {
                    'label': f"המרה לשער {curr['name']}",
                    'value': f"{curr['symbol']} {value} (שער: {rates[selected_code]:.4f})"
                }
            else:
                result = {
                    'label': f"המרה למטבע {selected_code}",
                    'value': f"{value} (שער: {rates[selected_code]:.4f})"
                }
        except Exception:
            error = "אנא הזן סכום תקין."
    return render_template('currency.html',
                          result=result,
                          currencies=valid_currencies,
                          selected_code=selected_code,
                          error=error)

@app.route('/discount', methods=['GET', 'POST'])
def discount():
    result = None
    error = None
    if request.method == 'POST':
        try:
            price = float(request.form['price'])
            percent1 = float(request.form['percent1'])
            percent2 = float(request.form.get('percent2', 0) or 0)

            if price < 0 or not (0 <= percent1 <= 100) or not (0 <= percent2 <= 100):
                raise ValueError

            # חישוב הנחות
            first_discount = price * (percent1 / 100)
            intermediate_price = price - first_discount
            if percent2 > 0:
                second_discount = intermediate_price * (percent2 / 100)
                final_price = intermediate_price - second_discount
            else:
                second_discount = 0
                final_price = intermediate_price

            total_discount = price - final_price
            effective_percent = 100 * (1 - final_price / price) if price else 0

            # התאמת טקסט הכותרת
            if percent2 > 0:
                label = f"המחיר אחרי {percent1:.2f}% ועוד {percent2:.2f}% הנחה"
            else:
                label = f"המחיר אחרי {percent1:.2f}% הנחה"

            result = {
                'label': label,
                'value': f"{final_price:.2f} ₪",
                'discount': f"חסכת: {total_discount:.2f} ₪ בסך הכל",
                'effective_percent': f"{effective_percent:.2f}"
            }
        except Exception:
            error = "אנא מלא ערכים תקינים בלבד"
    return render_template('discount.html', result=result, error=error)
@app.route("/about")
def about():
    return render_template("about.html")

@app.route("/privacy")
def privacy():
    return render_template("privacy.html")

@app.route('/accessibility-statement')
def accessibility_statement():
    """דף הצהרת נגישות (רשות)"""
    return render_template('accessibility-statement.html')

if __name__ == "__main__":
    app.run(debug=True)
