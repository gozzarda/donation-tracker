import csv
import re
from starlette.applications import Starlette
from starlette.endpoints import HTTPEndpoint
# from starlette.staticfiles import StaticFiles
from starlette.responses import HTMLResponse, RedirectResponse
from starlette.templating import Jinja2Templates
import uvicorn

templates = Jinja2Templates(directory='templates')

app = Starlette(debug=True)
# app.mount('/static', StaticFiles(directory='statics'), name='static')

COST_PER_CAN = 75
NUM_RECENTS = 5
CURRENCY_MINOR = 100

TAG_PATTERN = '#\\S+'

DATA_FILE = '/data/donations.csv'
OPTS_FILE = '/data/form_opts.csv'

donations = []
donation_total = 0
tag_totals = {}
form_opts = []

def csv_read_rows(path):
    try:
        with open(path) as fp:
            reader = csv.reader(fp)
            return list(reader)
    except:
        open(path, 'w').close()
        return []

def csv_push_row(path, row):
    with open(path, 'a+', newline='') as fp:
        writer = csv.writer(fp)
        writer.writerow(row)

@app.on_event('startup')
async def load():
    for row in csv_read_rows(DATA_FILE):
        amount = int(row[0])
        description = row[1]
        add_donation(amount, description, save=False)
    for row in csv_read_rows(OPTS_FILE):
        amount = int(row[0])
        description = row[1]
        add_form_opt(amount, description, save=False)

def add_donation(amount, description, save=True):
    amount = int(amount)
    description = str(description)
    donations.append((amount, description))
    global donation_total
    donation_total += amount
    for tag in re.findall(TAG_PATTERN, description):
        tag_totals[tag] = tag_totals.get(tag, 0) + amount
    if save:
        csv_push_row(DATA_FILE, (amount, description))

def add_form_opt(amount, description, save=True):
    form_opts.append((amount, description))
    if save:
        csv_push_row(OPTS_FILE, (amount, description))

def render_currency(amount):
    return '${:,}.{:02d}'.format(amount // CURRENCY_MINOR, amount % CURRENCY_MINOR)
templates.env.globals['render_currency'] = render_currency

def get_top_tags():
    top_tags = [ (v, k) for k, v in tag_totals.items() ]
    top_tags.sort(reverse=True)
    return top_tags

@app.route('/')
class Homepage(HTTPEndpoint):
    async def get(self, request):
        template = 'index.html'
        global donation_total
        recents = donations[-1:-(NUM_RECENTS+1):-1]
        num_cans = donation_total // COST_PER_CAN
        context = {
            'request': request,
            'donation_total': donation_total,
            'recents': recents,
            'num_cans': num_cans,
            'top_tags': get_top_tags(),
        }
        return templates.TemplateResponse(template, context)

@app.route('/update')
class Update(HTTPEndpoint):
    async def get(self, request):
        template = 'update.html'
        global donation_total
        context = {
            'request': request,
            'donation_total': donation_total,
            'form_opts': form_opts,
        }
        return templates.TemplateResponse(template, context)

    async def post(self, request):
        form = await request.form()
        amount = int(form.get('amount', default=float(form.get('major_amount', default=0)) * CURRENCY_MINOR))
        description = form['description']
        if form.get('action') == 'Save':
            add_form_opt(amount, description)
        else:
            add_donation(amount, description)
        return RedirectResponse(url='/update')
