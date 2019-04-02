import logging
import os
import xml.dom.minidom
from pprint import pprint

from django.template import Template

from django.conf import settings

import iso8601
from django.template import Context
from pysimplesoap import simplexml
from pysimplesoap.client import SoapClient, SoapFault, soap_namespaces

# Workaround timezone parsing ('Z')
# TODO: send issue and patch upstream
import datetime
simplexml.TYPE_UNMARSHAL_FN[datetime.datetime] = iso8601.parse_date


LOG = logging.getLogger(__name__)


def _log_response(response):
    if LOG.isEnabledFor(logging.DEBUG):
        LOG.debug(pprint(response))


def check_papi_key(papi_key):
    """ use papi key to get user from Stadlander
    Return user if papi key is valid (create if necessary)
    """
    trace = settings.DEBUG
    client = SoapClient(
        location=settings.STADLANDER_WEB_SERVICE_URL,
        action=settings.STADLANDER_WEB_SERVICE_URL,
        namespace=settings.STADLANDER_WEB_SERVICE_URL,
        soap_ns='soap', trace=trace, ns=False, exceptions=True,
    )

    papi_key = papi_key
    soap_uri = soap_namespaces['soap']
    soap_response = None
    try:
        LOG.info("Stadlander utils check_papi_key {0}".format(papi_key))
        #
        if settings.STADLANDER_WEB_SERVICE_API_CALL == "getQoinData":
            soap_response = client.GetQoinData(papi_key=papi_key)
        #
        if settings.STADLANDER_WEB_SERVICE_API_CALL == "getPositoosData":
            soap_response = client.GetPositoosData(papi_key=papi_key)
        #
        _log_response(soap_response)
    except SoapFault, sf:
        LOG.error(
            "Problem connecting to STADLANDER_WEB_SERVICE_URL {0}".format(
                settings.STADLANDER_WEB_SERVICE_URL))
        LOG.error("SoapFault {0}".format(sf))
        return None
    except Exception, e:
        LOG.error("Error with soap call {0}".format(e))
        return None

    body_children = soap_response('Body', ns=soap_uri).children()
    items_dom = xml.dom.minidom.parseString(body_children.as_xml())
    items_list_dom = items_dom.getElementsByTagName('item')
    items = {}
    # <item><key xsi:type="xsd:string">rel_number</key><value xsi:type="xsd:string">91876</value></item>
    # <item><key xsi:type="xsd:string">gender</key><value xsi:type="xsd:string"> </value></item>
    # <item><key xsi:type="xsd:string">initials</key><value xsi:type="xsd:string">A.</value></item>
    # <item><key xsi:type="xsd:string">insert</key><value xsi:type="xsd:string"/></item>
    # <item><key xsi:type="xsd:string">last_name</key><value xsi:type="xsd:string">Faas</value></item>
    # <item><key xsi:type="xsd:string">mail</key><value xsi:type="xsd:string">stvb@ecommany.com</value></item>
    # <item><key xsi:type="xsd:string">date_of_birth</key><value xsi:type="xsd:string">28-12-1954</value></item>
    # <item><key xsi:type="xsd:string">street</key><value xsi:type="xsd:string">Julianastraat</value></item>
    # <item><key xsi:type="xsd:string">number</key><value xsi:type="xsd:int">13</value></item>
    # <item><key xsi:type="xsd:string">addition</key><value xsi:type="xsd:string"/></item>
    # <item><key xsi:type="xsd:string">zip_code</key><value xsi:type="xsd:string">4661 JN</value></item>
    # <item><key xsi:type="xsd:string">residence</key><value xsi:type="xsd:string">HALSTEREN</value></item>
    for item in items_list_dom:
        key = get_node_text(item.getElementsByTagName('key')[0].childNodes)
        value = get_node_text(item.getElementsByTagName('value')[0].childNodes)
        items[key] = value

    return items


def get_node_text(nodelist):
    """
    Utility method for grabbing text from a minidom XML node
     - http://docs.python.org/library/xml.dom.minidom.html#dom-objects
    """
    rc = []
    for node in nodelist:
        if node.nodeType == node.TEXT_NODE:
            rc.append(node.data)
    return ''.join(rc)


def update_stadlander_status(persoonsnummer, active):
    """
    Update Stadlander Tobias system when a tenant's active status changes
    :param persoonsnummer:
    :param active:
    :return:
    """
    import requests

    request_uri = getattr(
        settings, "STADLANDER_TOBIAS_URL",
        'https://test.datarotonde.com/WcfBus/V1/Router.svc/soap/'
        'RequestReply')

    default_certificate_path = os.path.join(
        settings.PROJECT_DIR, 'stadlander', 'tobias',
        'stadlander_demo_soap_ssl.pem')
    certificate_path = getattr(
        settings, "STADLANDER_TOBIAS_CERT_PATH", default_certificate_path)

    default_body_template_path = os.path.join(
        settings.PROJECT_DIR, 'stadlander', 'tobias',
        'request.xml')
    body_template_path = getattr(
        settings, "STADLANDER_TOBIAS_TEMPLATE_PATH", default_body_template_path)

    LOG.info("update_stadlander_status: request_uri=%s" % request_uri)
    LOG.info("update_stadlander_status: certificate_path=%s" % certificate_path)
    LOG.info("update_stadlander_status: body_template_path=%s" % body_template_path)

    # active:    < !-- Mogelijke    waarden: 'True', 'False'. -->
    # rel_number <!-- Persoonsnummer zoals bekend bij Stadlander -->
    context = {
        'rel_number': persoonsnummer,
        'active': active
    }

    body_template = open(body_template_path).read()
    body = Template(body_template).render(Context(context)).rstrip()

    LOG.info("update_stadlander_status: body=%s" % body)
    s = requests.Session()
    s.cert = certificate_path
    s.headers = {'Content-Type': 'text/xml'}

    response = s.post(request_uri, data=body)

    LOG.info("update_stadlander_status: response=%s" % response)
