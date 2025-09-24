import os
from dotenv import load_dotenv
from flask import Flask, g, request, url_for
from flask_login import LoginManager, current_user
from flask_migrate import Migrate
from flask_wtf import CSRFProtect
from app.classes.helper import convert_to_seven_digits, generate_rsa_key_pair, get_or_create_visit_count
from app.db import db
from app.models import State_UT,District,Block,User
from app.routes.routes import blp as routesBlueprint
from app.routes.auth import blp as authBlueprint
from app.apis.api import blp as apiBlueprint
from app.apis.lms import blp as apilmsBlueprint
from app.apis.lrs import blp as apilrsBlueprint
from app.routes.dashboard import blp as dashboardBlueprint


def create_app():
    load_dotenv()
    app = Flask(__name__)

    # App Configuration
    app.config['SECRET_KEY'] = os.getenv('SECRET_KEY',"you-will-never-guess")

    # SCORM Folders
    directory_path = os.path.dirname(__file__)
    app.config['UPLOAD_FOLDER'] = os.path.join(directory_path,'static/uploads')
    app.config['SCORM_FOLDER'] = os.path.join(directory_path,'static/scorm_packages')
    app.config['MAX_CONTENT_LENGTH'] = 200 * 1024 * 1024

    # Create necessary directories
    os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
    os.makedirs(app.config['SCORM_FOLDER'], exist_ok=True)

    # DB Config
    app.config['SQLALCHEMY_DATABASE_URI'] = os.getenv('DATABASE_URL','postgresql://db_master:w24JyTn0SIEHfS@144.24.103.183:5432/iSaksham_dashboard')
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    app.config['PROPAGATE_EXCEPTIONS'] = True
    app.config['WTF_CSRF_ENABLED'] = False
    public_key_pem, private_key_pem = generate_rsa_key_pair()
    app.config['PUBLIC_KEY'] = public_key_pem
    app.config['PRIVATE_KEY'] = private_key_pem

    # Initialize
    db.init_app(app)
    migrate = Migrate(app, db)
    csrf = CSRFProtect(app)
    login_manager=LoginManager(app)
    # create_db(app)

    @login_manager.user_loader
    def load_user(user_id):
        return User.get_user_by_id(user_id)

    login_manager.login_view = "auth.login"
    login_manager.login_message = "Access is restricted. Please login"
    login_manager.login_message_category = "info"
    # Register Blueprint
    app.register_blueprint(routesBlueprint)
    app.register_blueprint(authBlueprint)
    app.register_blueprint(apiBlueprint)
    app.register_blueprint(apilmsBlueprint)
    app.register_blueprint(apilrsBlueprint)
    from app.routes.admin import blp as adminBlueprint
    app.register_blueprint(adminBlueprint)
    app.register_blueprint(dashboardBlueprint)

    # --- inject navbar menus ---
    # @app.context_processor
    # def inject_navbar():
    #     if current_user.is_authenticated:
    #         menus = current_user.get_menus()
    #     else:
    #         menus = []
    #     return dict(nav_menus=menus)
    
    @app.context_processor
    def inject_global_template_variables():
        """Injects variables accessible in all templates, including dynamic nav and page info."""
        try:
            current_visit_count = convert_to_seven_digits(g.get('visit_count', get_or_create_visit_count()))
            user_name = current_user.name if current_user.is_authenticated else ""
            # average_rating = Feedback.get_average()
            average_rating = None
            if average_rating is None:
                average_rating = 0.0

            # --- Dynamic Navigation and Page Info ---
            nav_menus = []
            page_title = "Home"
            page_subtitle = "MGNREGS Digital Learning Platform"
            breadcrumbs = [{'url': url_for('routes.index'), 'name': 'Home'}] # Default Home breadcrumb

            if current_user.is_authenticated:
                all_accessible_menus = current_user.get_menus() # Get flat list for easy URL lookup
                nav_menus_structured = current_user.get_structured_menus() # Get hierarchical for nav rendering
                
                nav_menus = nav_menus_structured # Use structured for primary navigation

                # Find the current active menu item based on the request path
                active_menu_item = None
                for menu in all_accessible_menus:
                    # Check if the menu's URL exactly matches the request path or starts with it
                    # Consider more robust URL matching if your menu URLs are not direct routes
                    if request.path == menu.url or (menu.url != '/' and request.path.startswith(menu.url + '/')):
                        active_menu_item = menu
                        break
                
                if active_menu_item:
                    page_title = active_menu_item.name
                    # You might need an extra field in MenuItem for a specific subtitle
                    # For now, let's use a generic subtitle or leave it empty if not defined
                    page_subtitle = f"Current page: {active_menu_item.name}" 
                    
                    # Build breadcrumbs by tracing back up the parent chain
                    temp_breadcrumbs = []
                    current_breadcrumb_item = active_menu_item
                    while current_breadcrumb_item:
                        temp_breadcrumbs.insert(0, {'url': current_breadcrumb_item.url, 'name': current_breadcrumb_item.name})
                        current_breadcrumb_item = current_breadcrumb_item.parent # Assumes 'parent' is loaded

                    # Add the Home breadcrumb if not already the first one
                    if not temp_breadcrumbs or temp_breadcrumbs[0]['url'] != url_for('routes.index'):
                         temp_breadcrumbs.insert(0, {'url': url_for('routes.index'), 'name': 'Home'})
                    
                    breadcrumbs = temp_breadcrumbs
                else:
                    # Fallback for pages not directly linked to a menu item (e.g., admin login, error pages)
                    # You could define specific titles/subtitles for these
                    if request.endpoint: # If a Flask endpoint exists
                        page_title = request.endpoint.replace('_', ' ').title()
                        page_subtitle = f"Viewing {page_title}"
                        breadcrumbs.append({'url': request.path, 'name': page_title})

            # Override/extend default breadcrumbs if defined in a view with `g.breadcrumbs`
            if hasattr(g, 'breadcrumbs'):
                breadcrumbs = g.breadcrumbs

            # Override/extend default titles if defined in a view with `g.page_title`/`g.page_subtitle`
            if hasattr(g, 'page_title'):
                page_title = g.page_title
            if hasattr(g, 'page_subtitle'):
                page_subtitle = g.page_subtitle

            return {
                'visit_count': current_visit_count,
                'name': user_name,
                'average_rating': round(average_rating, 1),
                'nav_menus': nav_menus, # Structured menus for navigation
                'page_title': page_title,
                'page_subtitle': page_subtitle,
                'breadcrumbs': breadcrumbs
            }
        except Exception as ex:
            # error_logger.error(f"Error injecting template context: {ex}", exc_info=True)
            return {
                'visit_count': '0000000', 'name': '', 'average_rating': 0.0,
                'nav_menus': [], 'page_title': 'Error', 'page_subtitle': 'Something went wrong',
                'breadcrumbs': [{'url': url_for('routes.index'), 'name': 'Home'}]
            }


    return app