from jinja2 import Template
from matrix_client.room import Room
from vibora import Request
from vibora.responses import JsonResponse

alertmanager_template = open('templates/alertmanager.jinja', 'r').read()


async def alertmanager(request: Request, matrix_link):
    values = await request.json()

    templ = Template(alertmanager_template)
    html_res = templ.render(**values)
    text_res = f"[{values['status'].capitalize()}] {values['groupLabels']['alertname']}"

    alert_room = matrix_link.rooms['alert_room']  # type: Room
    alert_room.send_html(html_res, text_res)

    return JsonResponse({})
