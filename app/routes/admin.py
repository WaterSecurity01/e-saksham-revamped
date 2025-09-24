from flask import Blueprint, flash, redirect, render_template, request, url_for

from app.classes.forms import RoleForm, menuItemForm
from app.models.menu_in_role import MenuInRole
from app.models.menu_item import MenuItem
from app.models.role import Role
from app.models.user_in_role import UserInRole


blp = Blueprint('admin',__name__,url_prefix='/admin')

@blp.route('/roles',methods=['GET','POST'])
def roles():
    form = RoleForm()
    if form.validate_on_submit():
        role = Role.get_role_by_name(form.name.data)
        if not role:
            new_role = Role(name=form.name.data, description=form.description.data)
            new_role.save()
            flash("Role added successfully!", "success")
            return redirect(url_for("admin.roles"))
        else:
            flash("Role already exists!", "success")

    all_roles = Role.query.all()
    return render_template("admin/roles.html", roles=all_roles, form=form)

@blp.route('/menu_items',methods=['GET','POST'])
def menu_items():
    form = menuItemForm()
    all_menu_items = MenuItem.query.all()
    form.parent_id.choices = [(-1, "Select Parent"), (0, "Root Node")]
    form.parent_id.choices += [(item.id, item.name) for item in all_menu_items]
    if form.validate_on_submit():
        menuItem = MenuItem.get_menuItem_by_name(form.name.data)
        if not menuItem:
            new_menuItem = MenuItem(form.name.data,form.url.data,form.icon.data,form.parent_id.data,form.order_index.data)
            new_menuItem.save()
            flash("Menu item added successfully!", "success")
            return redirect(url_for("admin.menu_items"))
        else:
            flash("Menu item already exists!", "success")
        
    return render_template("admin/menu_items.html", menu_items=all_menu_items, form=form)

@blp.route('/users_in_roles', methods=['GET','POST'])
def users_in_roles():
    if request.method=='POST':
        print('post method')
        pass
    roles = Role.get_all()
    user_in_roles = UserInRole.get_all()
    for i in range(10):
        user_in_roles.append({"serial": i + 1,"user_id": i,"username": "username_" + str(i),"roles": ["user"]})
    return render_template('admin/users_in_roles.html', roles = roles, users=user_in_roles)

@blp.route("/menu_in_roles")
def menu_in_roles():
    roles = Role.get_all()
    menu_in_roles = MenuInRole.get_all()
    return render_template('admin/menu_in_roles.html', roles = roles, menu_items = menu_in_roles)