from django.conf import settings
from django.conf.urls.static import static
from django.urls import path

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
    path('wishlist/<slug:slug>/', views.wishlist_toggle, name='wishlist_toggle'),

    # Sales & Payment module URL routes
    path('cart/', views.cart, name='cart'),
    path('checkout/', views.checkout, name='checkout'),
    path('tracking/', views.tracking, name='tracking'),
    path('admin-dashboard/', views.admin_dashboard, name='admin_dashboard'),
    path('admin-orders/', views.admin_orders, name='admin_orders'),
    path('admin-promotions/', views.admin_promotions, name='admin_promotions'),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
