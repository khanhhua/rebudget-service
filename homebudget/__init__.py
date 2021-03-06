from pyramid.config import Configurator
# See http://docs.pylonsproject.org/projects/pyramid_cookbook/en/latest/database/sqlalchemy.html
# See http://docs.pylonsproject.org/projects/pyramid_cookbook/en/latest/database/index.html
from pyramid.httpexceptions import HTTPBadRequest
from pyramid.session import SignedCookieSessionFactory

from sqlalchemy import engine_from_config
from sqlalchemy.orm import sessionmaker

import jwt
from os import environ

JWT_SECRET = environ.get('JWT_SECRET', None) or 's3cr3t'


def main(global_config, **settings):
    """ This function returns a Pyramid WSGI application.
    """
    config = Configurator(settings=settings)
    config.include('pyramid_jinja2')
    config.add_jinja2_renderer('.html')

    config.include('.cors');
    # make sure to add this before other routes to intercept OPTIONS
    config.add_cors_preflight_handler()

    session_factory = SignedCookieSessionFactory('GPwzx57Dpsh2GPl')
    config.set_session_factory(session_factory)

    engine = engine_from_config(settings, prefix='sqlalchemy.')
    config.registry.dbmaker = sessionmaker(bind=engine)
    config.add_request_method(db, reify=True)

    config.add_request_method(current_user, reify=True)

    config.add_static_view('static', 'static', cache_max_age=3600)
    config.add_route('home', '/')
    config.add_route('facebook_callback', '/auth/facebook')

    # - - - - - - - - - - - - - - - - - - - - - - - -
    config.add_route('api_link', '/api/link')
    config.add_route('api_quota', '/api/quota')
    config.add_route('api_settings', '/api/settings')
    # - - - - - - - - - - - - - - - - - - - - - - - -
    config.add_route('api_categories', '/api/categories')
    config.add_route('api_categories_id', '/api/categories/{id}')
    config.add_route('api_entries', '/api/entries')
    config.add_route('api_entries_id', '/api/entries/{id}')

    config.scan()
    return config.make_wsgi_app()


def db(request):
    maker = request.registry.dbmaker
    session = maker()

    def cleanup(request):
        if request.exception is not None:
            session.rollback()
        else:
            session.commit()
        session.close()
    request.add_finished_callback(cleanup)

    return session


def current_user(request):
    if 'Authorization' in request.headers and request.headers['Authorization'].index('jwt ') == 0:
        jwt_payload = request.headers['Authorization'][4:]
        if len(jwt_payload) == 0:
            raise HTTPBadRequest()

        try:
            decoded_payload = jwt.decode(jwt_payload, JWT_SECRET)
            return {
                'id': decoded_payload['sub'],
                'access_key': decoded_payload['access_key']
            }
        except jwt.ExpiredSignatureError:
            raise HTTPBadRequest()

    else:
        return None