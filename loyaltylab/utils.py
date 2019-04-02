import logging

from pysimplesoap.client import SoapClient
from pysimplesoap.simplexml import SimpleXMLElement

LOG = logging.getLogger(__name__)

# These are the three ClientGUIDs for the Loyalty Lab webservice
# - we can add additional IP addresses as needed
# D4B80983-5E23-4793-8A2B-3AB25384DAF3 212.48.69.196
# 0C87E8D4-3789-48B3-B3A9-45E6199E0888 143.159.203.207
# E4D5C977-BF55-45F5-851B-CD65D598D112 212.48.68.120
#
# this one's for Al's current IP address (likely to change):
ll_username = "0C87E8D4-3789-48B3-B3A9-45E6199E0888"

# SQL Ids, to be supplied by LL.
# There is one for each different GetData instruction we need to use.
# So far we just have:
#  TestQuery - list all the instructions we are entitled to use
ll_test_sqlid = "71cc20c5-5636-de11-8bb6-002219910e09"  #' TestQuery'
ll_employee_data_sqlid = "cc00eb83-6fe7-4605-8ada-989852f14edd"
  # dummy test transaction

ll_wsdl_url = "https://secure.data.loyaltylab.nl"  \
              "/llextraction/llextractionwebservice.asmx?WSDL"

def _construct_parameter_xml(param_dict):
    param_list = []
    for key, value in param_dict.items():
        param_list.append("""<Parameter Name="@{0}">{1}</Parameter>""".format(
            key, value)   # TODO urlencode these?
        )
    return """<Parameters>{0}</Parameters>""".format("".join(param_list))


def ll_get_data(
    UserName=ll_username, SqlId="", XMLParameters="", trace=False):
    client = SoapClient(wsdl=ll_wsdl_url, trace=trace)
    response = client.GetData(
        UserName=UserName, SqlId=SqlId, XMLParameters=XMLParameters)
    return response


def notify_ll_of_new_user():
    """Notify Loyalty Lab of a new user

    #2874 LL needs to know about new users. Call this when
          a user activates their profile.
          (Done in asignal handler in icare4u_front.profile.models)
    """
    LOG.info("Notifying Loyalty Lab of new user")
    # TODO!


def notify_ll_user_transaction():
    """Notify Loyalty Lab of a new transaction

    #2874 LL needs to know about all transactions (check this!)
    """
    LOG.info("Notifying Loyalty Lab of transaction")
    # TODO!


def ll_list_instructions():
    """List all the instructions we are entitled to use

    Call GetData with the TestQuery instruction, and extract the list of valid
    instructions from the response
    """
    instructions = []
    response = ll_get_data(SqlId=ll_test_sqlid)
    result = response['GetDataResult'].Result.Result
    if int(result) != 1:
        LOG.error(
            "Unexpected Result from GetData: {0} (expected 1)\n"  \
            "   Descripton: {1};\n   ErrorDescripton: {2}\n".format(
            result,
            response['GetDataResult'].Result.Description,
            response['GetDataResult'].Result.ErrorDescription))
        return instructions
    result_table = response['GetDataResult'].ResultTable
    # TODO: not sure how this works when there's more than one...
    LOG.debug("{0}\n   {1}\n   {2}".format(
        result_table.Name, result_table.Description, result_table.guid))
    instructions.append(str(result_table.Name))
    LOG.debug(instructions)
    return instructions


def ll_get_employee_data(name, monthly_salary, contract_start_date):
    """Get employee details for an individual

    Call GetData with the 'Ophalen Employee data' instruction,
    and extract salary and contract end date from the response
    """
    parameter_xml = _construct_parameter_xml({
        'EmployeeName': name,
        'MonthlySalary': monthly_salary,
        'ContractStartDate': contract_start_date,
        })
    response = ll_get_data(
        SqlId=ll_employee_data_sqlid,
        XMLParameters=parameter_xml)
    result = response['GetDataResult'].Result.Result
    if int(result) != 1:
        LOG.error(
            "Unexpected Result from GetData: {0} (expected 1)\n"  \
            "   Descripton: {1};\n   ErrorDescripton: {2}\n".format(
            result,
            response['GetDataResult'].Result.Description,
            response['GetDataResult'].Result.ErrorDescription))
        return instructions
    result_table = response['GetDataResult'].ResultTable
    # TODO: not sure how this works when there's more than one...
    LOG.info(result_table)
    LOG.debug("{0}\n   {1}\n   {2}".format(
        result_table.EmployeeName, result_table.YearlySalary, result_table.ContractEndDate))
    return (str(result_table.YearlySalary), str(result_table.ContractEndDate))
