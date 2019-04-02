# encoding: utf-8
"""
Invoice PDF drawing functions adapted from:
https://github.com/simonluijk/django-invoice/blob/master/invoice/pdf.py

BSD licensed.
"""
import logging
import os

from reportlab.pdfgen.canvas import Canvas
from reportlab.platypus import Table
from reportlab.lib import utils
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import cm

from django.conf import settings
from django.utils.translation import ugettext as _

logger = logging.getLogger(__name__)

logo_image = getattr(
    settings, 'LOGO_IMG',
    os.path.join(settings.PROJECT_DIR, 'static/img/logo.png'))


def get_image_width_height(path, width=4*cm):
    image = utils.ImageReader(path)
    image_width, image_height = image.getSize()
    aspect = image_height / float(image_width)

    return width, width * aspect


def draw_header(canvas):
    """ Draws the invoice header """
    try:
        width, height = get_image_width_height(logo_image)
        canvas.drawImage(logo_image, 1.0 * cm, -2.5 * cm, width, height)
    except IOError:
        # Logo image file does not exist.
        logger.error(u"The image logo file for generating PDFs doesn't exist.")


def draw_address(canvas):
    """ Draws the business address """
    business_details = (
        _(u'{0}').format(getattr(settings, 'CC3_SYSTEM_NAME', 'TradeQoin')),
        _(u'Postbus 178'),
        _(u'5060AD Oisterwijk'),
        _(u'info@positoos.nl'),
        _(u'KvK:17229441 - BTW:81966.105.B.01 - Rabo: NL15RABO0154443476')
    )
    canvas.setFont('Helvetica', 9)
    textobject = canvas.beginText(6 * cm, -1.0 * cm)
    for line in business_details:
        textobject.textLine(line)
    canvas.drawText(textobject)
    canvas.line(1 * cm, -3.0 * cm, 20 * cm, -3.0 * cm)

def draw_footer(canvas, invoice):
    """ Draws the invoice footer """
    if invoice.get_total() > 0:
        note = (
            _(u'Gelieve dit bedrag binnen 14 dagen over te maken op rekening'),
            _(u'NL15 RABO 0154443476 t.n.v. Stichting Derdengelden Positoos'),
            )
    else:
        note = (
            _(u'Wij zullen dit bedrag binnenkort overmaken naar de bij ons bekende bankrekening van uw bedrijf.'),
            )
    textobject = canvas.beginText(1 * cm, -27 * cm)
    for line in note:
        textobject.textLine(line)
    canvas.drawText(textobject)


def draw_pdf(buffer, invoice):
    """ Draws the invoice """
    canvas = Canvas(buffer, pagesize=A4)
    canvas.translate(0, 29.7 * cm)
    canvas.setFont('Helvetica', 10)

    canvas.saveState()
    draw_header(canvas)
    canvas.restoreState()

    canvas.saveState()
    draw_footer(canvas, invoice)
    canvas.restoreState()

    canvas.saveState()
    draw_address(canvas)
    canvas.restoreState()

    currency_symbol = invoice.currency.symbol

    # Client address
    profile = invoice.to_user.cc3_profile
    textobject = canvas.beginText(1.5 * cm, -4.5 * cm)

    textobject.textLine(_(u'Afrekening'))
    textobject.textLine('')

    textobject.textLine(profile.business_name)
    textobject.textLine(_(u"t.a.v. de Crediteurenadministratie"))
    textobject.textLine(profile.address)
    textobject.textLine(u"{0} {1}".format(profile.postal_code, profile.city))
    textobject.textLine(unicode(profile.country.name))
    canvas.drawText(textobject)

    # Info
    textobject = canvas.beginText(1.5 * cm, -8.75 * cm)
    textobject.textLine(_(u'Invoice no: {0}'.format(invoice.inv_no)))
    textobject.textLine(_(u'Invoice Date: {0}'.format(
        invoice.inv_date.strftime('%d %b %Y'))))
    canvas.drawText(textobject)

    # Items
    data = [
        [_(u'Description'), _(u'Total')]
    ]

    for item in invoice.lines.all():
        data.append([
            item.description,
            u"{0:.2f} {1}".format(item.grand_total, currency_symbol),
        ])

#    data.append([u'', _(u'Sub total:') + u" {0:.2f} {1}".format(
#        invoice.get_sub_total(), currency_symbol)])
#    data.append([u'',  _(u'Tax:') + u" {0:.2f} {1}".format(
#        invoice.get_tax(), currency_symbol)])
    data.append([u'',  _(u'Total:') + u" {0:.2f} {1}".format(
        invoice.get_total(), currency_symbol)])

    table = Table(data, colWidths=[14.5 * cm, 4 * cm])
    table.setStyle([
        ('FONT', (0, 0), (-1, -1), 'Helvetica'),
        ('FONTSIZE', (0, 0), (-1, -1), 10),
        ('TEXTCOLOR', (0, 0), (-1, -1), (0.2, 0.2, 0.2)),
        ('GRID', (0, 0), (-1, -4), 1, (0.7, 0.7, 0.7)),
        ('GRID', (-2, -3), (-1, -1), 1, (0.7, 0.7, 0.7)),
        ('ALIGN', (-1, 0), (-1, -1), 'RIGHT'),
        ('BACKGROUND', (0, 0), (-1, 0), (0.8, 0.8, 0.8)),
    ])
    table_widht, table_height, = table.wrapOn(canvas, 15 * cm, 19 * cm)
    table.drawOn(canvas, 1.5 * cm, -10 * cm - table_height)

    canvas.showPage()
    canvas.save()
