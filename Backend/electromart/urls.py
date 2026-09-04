from django.conf import settings
from django.conf.urls.static import static
from django.urls import path

from accounts import views as accounts_views
from catalogue import views as catalogue_views
from interaction import views as interaction_views


urlpatterns = [
    # ============================================================
    # STOREFRONT
    # ============================================================
    path('', catalogue_views.home, name='home'),
    path('category/<slug:slug>/', catalogue_views.product_list, name='product_list'),
    path('product/<slug:slug>/', catalogue_views.product_detail, name='product_detail'),
    path('search/', catalogue_views.search, name='search'),
    path('api/suggest/', catalogue_views.search_suggest, name='search_suggest'),
    path('compare/', catalogue_views.compare, name='compare'),
    path('compare/clear/', catalogue_views.compare_clear, name='compare_clear'),
    path('compare/<slug:slug>/', catalogue_views.compare_toggle, name='compare_toggle'),
    path('wishlist/', catalogue_views.wishlist, name='wishlist'),

    # ============================================================
    # ACCOUNTS - LOC
    # ============================================================
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

    # ============================================================
    # MINH
    # ============================================================

    # CV70 - News / FAQ / Feedback
    path('news/', catalogue_views.news, name='news'),
    path('news/<slug:slug>/', catalogue_views.news_detail, name='news_detail'),
    path('feedback/', catalogue_views.feedback, name='feedback'),
    path('faq/', catalogue_views.faq, name='faq'),

    # CV70 - Admin News
    path('admin/news/', catalogue_views.admin_news, name='admin_news'),
    path('admin/news/data/', catalogue_views.admin_news_data, name='admin_news_data'),
    path('admin/news/create/', catalogue_views.admin_news_create, name='admin_news_create'),
    path('admin/news/<str:news_id>/update/', catalogue_views.admin_news_update, name='admin_news_update'),
    path('admin/news/<str:news_id>/hidden/', catalogue_views.admin_news_hidden, name='admin_news_hidden'),
    path('admin/news/<str:news_id>/delete/', catalogue_views.admin_news_delete, name='admin_news_delete'),

    # CV70 - Admin Feedback
    path('admin/feedback/', catalogue_views.admin_feedback, name='admin_feedback'),
    path('admin/feedback/data/', catalogue_views.admin_feedback_data, name='admin_feedback_data'),
    path('admin/feedback/<str:feedback_id>/status/', catalogue_views.admin_feedback_status, name='admin_feedback_status'),
    path('admin/feedback/<str:feedback_id>/reply/', catalogue_views.admin_feedback_reply, name='admin_feedback_reply'),

    # CV71 - Admin Moderation
    path('admin/moderation/', catalogue_views.admin_moderation, name='admin_moderation'),
    path('admin/moderation/data/', catalogue_views.admin_moderation_data, name='admin_moderation_data'),
    path('admin/moderation/reviews/<str:review_id>/hidden/', catalogue_views.admin_moderation_review_hidden, name='admin_moderation_review_hidden'),
    path('admin/moderation/comments/<str:comment_id>/hidden/', catalogue_views.admin_moderation_comment_hidden, name='admin_moderation_comment_hidden'),
    path('admin/moderation/comments/<str:comment_id>/reply/', catalogue_views.admin_moderation_comment_reply, name='admin_moderation_comment_reply'),

    # CV42 / CV69 - Interaction
    path('product/<slug:product_slug>/comment/', interaction_views.submit_comment, name='submit_comment'),
    path('product/<slug:product_slug>/comment/<str:comment_id>/edit/', interaction_views.edit_comment, name='edit_comment'),
    path('product/<slug:product_slug>/comment/<str:comment_id>/hide/', interaction_views.hide_comment, name='hide_comment'),
    path('product/<slug:product_slug>/comment/<str:comment_id>/unhide/', interaction_views.unhide_comment, name='unhide_comment'),

    # CV65 - Admin Category + Dynamic Spec Template
    path('admin/categories/', catalogue_views.admin_categories, name='admin_categories'),
    path('admin/categories/data/', catalogue_views.admin_categories_data, name='admin_categories_data'),
    path('admin/categories/create/', catalogue_views.admin_category_create, name='admin_category_create'),
    path('admin/categories/<str:category_id>/update/', catalogue_views.admin_category_update, name='admin_category_update'),
    path('admin/categories/<str:category_id>/hidden/', catalogue_views.admin_category_hidden, name='admin_category_hidden'),
    path('admin/categories/<str:category_id>/spec-fields/create/', catalogue_views.admin_category_spec_create, name='admin_category_spec_create'),
    path('admin/categories/<str:category_id>/spec-fields/<str:field_key>/update/', catalogue_views.admin_category_spec_update, name='admin_category_spec_update'),
    path('admin/categories/<str:category_id>/spec-fields/<str:field_key>/delete/', catalogue_views.admin_category_spec_delete, name='admin_category_spec_delete'),
    path('admin/categories/<str:category_id>/delete/', catalogue_views.admin_category_delete, name='admin_category_delete'),

    # CV66 - Admin Product
    path('admin/products/', catalogue_views.admin_products, name='admin_products'),
    path('admin/products/data/', catalogue_views.admin_products_data, name='admin_products_data'),
    path('admin/products/create/', catalogue_views.admin_product_create, name='admin_product_create'),
    path('admin/products/<str:product_id>/data/', catalogue_views.admin_product_detail, name='admin_product_detail'),
    path('admin/products/<str:product_id>/update/', catalogue_views.admin_product_update, name='admin_product_update'),
    path('admin/products/<str:product_id>/hidden/', catalogue_views.admin_product_hidden, name='admin_product_hidden'),
    path('admin/products/<str:product_id>/variants/', catalogue_views.admin_product_variants, name='admin_product_variants'),
    path('admin/categories/<str:category_id>/spec-template/', catalogue_views.admin_category_spec_template, name='admin_category_spec_template'),

    # CV67 - Admin Inventory
    path('admin/inventory/', catalogue_views.admin_inventory, name='admin_inventory'),
    path('admin/inventory/data/', catalogue_views.admin_inventory_data, name='admin_inventory_data'),
    path('admin/inventory/low-stock/', catalogue_views.admin_inventory_low_stock, name='admin_inventory_low_stock'),
    path('admin/inventory/adjust/', catalogue_views.admin_inventory_adjust, name='admin_inventory_adjust'),
    path('admin/inventory/movements/', catalogue_views.admin_inventory_movements, name='admin_inventory_movements'),

    # CV68 - Review / Rating
    path('product/<slug:product_slug>/review/', interaction_views.submit_review, name='submit_review'),
    path('product/<slug:product_slug>/review/me/', interaction_views.my_review, name='my_review'),
    path('product/<slug:product_slug>/review/edit/', interaction_views.edit_review, name='edit_review'),
    path('product/<slug:product_slug>/review/hide/', interaction_views.hide_review, name='hide_review'),
    path('product/<slug:product_slug>/review/unhide/', interaction_views.unhide_review, name='unhide_review'),

    # ============================================================
    # SALES & PAYMENT - TIN
    # ============================================================
    path('cart/', catalogue_views.cart, name='cart'),
    path('checkout/', catalogue_views.checkout, name='checkout'),
    path('tracking/', catalogue_views.tracking, name='tracking'),
    path('admin-dashboard/', catalogue_views.admin_dashboard, name='admin_dashboard'),
    path('admin-orders/', catalogue_views.admin_orders, name='admin_orders'),
    path('admin-promotions/', catalogue_views.admin_promotions, name='admin_promotions'),
]


if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
