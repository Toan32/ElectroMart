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
    path('news/', views.news, name='news'),
    path('feedback/', views.feedback, name='feedback'),
    path('faq/', views.faq, name='faq'),
    path('admin/categories/', views.admin_categories, name='admin_categories'),
    path('admin/products/', views.admin_products, name='admin_products'),
    path('admin/inventory/', views.admin_inventory, name='admin_inventory'),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
