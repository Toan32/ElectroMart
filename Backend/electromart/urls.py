from django.conf import settings
from django.conf.urls.static import static
from django.urls import path

from accounts import views as accounts_views
from catalogue import views

urlpatterns = [
    path('', views.home, name='home'),
    path('category/<slug:slug>/', views.product_list, name='product_list'),
    path('product/<slug:slug>/', views.product_detail, name='product_detail'),
    path('search/', views.search, name='search'),
    path('api/suggest/', views.search_suggest, name='search_suggest'),
    path('compare/', views.compare, name='compare'),
    path('compare/clear/', views.compare_clear, name='compare_clear'),
    path('compare/<slug:slug>/', views.compare_toggle, name='compare_toggle'),
    path('wishlist/', views.wishlist, name='wishlist'),
    # ------------------------------------------------------- accounts (Loc)
    path('accounts/register/', accounts_views.register, name='accounts_register'),
    path('accounts/activate/<str:token>/', accounts_views.activate, name='accounts_activate'),
    path('accounts/login/', accounts_views.login_view, name='accounts_login'),
    path('accounts/logout/', accounts_views.logout_view, name='accounts_logout'),
    path('accounts/forgot-password/', accounts_views.forgot_password, name='accounts_forgot_password'),
    path('accounts/reset-password/<str:token>/', accounts_views.reset_password, name='accounts_reset_password'),

    path('accounts/profile/', accounts_views.profile, name='accounts_profile'),
    path('accounts/profile/edit/', accounts_views.edit_profile, name='accounts_edit_profile'),
    path('accounts/profile/change-password/', accounts_views.change_password, name='accounts_change_password'),

    path('accounts/addresses/', accounts_views.address_book, name='accounts_address_book'),
    path('accounts/addresses/add/', accounts_views.address_add, name='accounts_address_add'),
    path('accounts/addresses/<str:address_id>/edit/', accounts_views.address_edit, name='accounts_address_edit'),
    path('accounts/addresses/<str:address_id>/delete/', accounts_views.address_delete, name='accounts_address_delete'),
    path('accounts/addresses/<str:address_id>/default/', accounts_views.address_set_default, name='accounts_address_set_default'),

    path('accounts/wholesale/register/', accounts_views.wholesale_register, name='accounts_wholesale_register'),
    path('accounts/wholesale/status/', accounts_views.wholesale_status, name='accounts_wholesale_status'),

    path('accounts/rfq/new/', accounts_views.rfq_create, name='accounts_rfq_create'),
    path('accounts/rfq/', accounts_views.rfq_list, name='accounts_rfq_list'),

    path('admin/users/', accounts_views.admin_manage_user, name='admin_manage_user'),
    path('admin/users/<str:user_id>/lock/', accounts_views.admin_toggle_lock, name='admin_toggle_lock'),
    path('admin/users/<str:profile_id>/wholesale-review/', accounts_views.admin_wholesale_review, name='admin_wholesale_review'),
    # ------------------------------------------------------- catalogue & content (Minh)
    path('news/', views.news, name='news'),
    path('feedback/', views.feedback, name='feedback'),
    path('faq/', views.faq, name='faq'),
    path('admin/categories/', views.admin_categories, name='admin_categories'),
    path('admin/products/', views.admin_products, name='admin_products'),
    path('admin/inventory/', views.admin_inventory, name='admin_inventory'),

    # ------------------------------------------------------- sales & payment (Tin)
    path('cart/', views.cart, name='cart'),
    path('checkout/', views.checkout, name='checkout'),
    path('tracking/', views.tracking, name='tracking'),
    path('admin-dashboard/', views.admin_dashboard, name='admin_dashboard'),
    path('admin-orders/', views.admin_orders, name='admin_orders'),
    path('admin-promotions/', views.admin_promotions, name='admin_promotions'),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
