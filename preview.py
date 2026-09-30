"""Serve the included Suraksha bundle and API together on localhost:5180."""
import os
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / 'backend'))
os.chdir(ROOT / 'backend')
os.environ.setdefault('NOTIFIER', 'log')

import uvicorn
from fastapi.staticfiles import StaticFiles
from starlette.exceptions import HTTPException
from starlette.responses import Response
from starlette.types import Scope
from app.main import create_app


class ConsoleFiles(StaticFiles):
    async def get_response(self, path: str, scope: Scope) -> Response:
        request_path = scope.get('path', '')
        if request_path == '/api' or request_path.startswith('/api/'):
            raise HTTPException(status_code=404)
        try:
            return await super().get_response(path, scope)
        except HTTPException as error:
            if error.status_code == 404 and not Path(path).suffix:
                return await super().get_response('index.html', scope)
            raise


def main() -> None:
    application = create_app()
    application.mount('/', ConsoleFiles(directory=ROOT / 'frontend/dist', html=True), name='console')
    uvicorn.run(application, host='127.0.0.1', port=5180)


if __name__ == '__main__':
    main()
