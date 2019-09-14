#!/usr/bin/env python3

from vibora import Request, Response, Vibora

from matrix_link import MatrixLink

vibora = Vibora()


@vibora.route('/')
async def home(request: Request):
    return Response("♫ knopfler up and running".encode())


if __name__ == "__main__":
    MatrixLink(vibora)
    vibora.run(debug=True, host='0.0.0.0', port=9282)
