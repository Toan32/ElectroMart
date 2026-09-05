from django.conf import settings
from django.conf.urls.static import static
from django.urls import path
from django.views.generic import RedirectView

from accounts import views as accounts_views
from catalogue import views
from interaction import views as interaction_views
from sales import views as sales_views

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

    path('accounts/orders/', sales_views.track_order, name='accounts_orders'),

    # ------------------------------------------------------- catalogue & content (Minh)
    path('news/', views.news, name='news'),
    path('news/<slug:slug>/', views.news_detail, name='news_detail'),
    path('feedback/', views.feedback, name='feedback'),
    path('faq/', views.faq, name='faq'),

    # Reviews and Q&A on a product page (CV42 / CV68 / CV69).
    path('product/<slug:product_slug>/review/', interaction_views.submit_review, name='submit_review'),
    path('product/<slug:product_slug>/review/me/', interaction_views.my_review, name='my_review'),
    path('product/<slug:product_slug>/review/edit/', interaction_views.edit_review, name='edit_review'),
    path('product/<slug:product_slug>/review/hide/', interaction_views.hide_review, name='hide_review'),
    path('product/<slug:product_slug>/review/unhide/', interaction_views.unhide_review, name='unhide_review'),
    path('product/<slug:product_slug>/comment/', interaction_views.submit_comment, name='submit_comment'),
    path('product/<slug:product_slug>/comment/<str:comment_id>/edit/', interaction_views.edit_comment, name='edit_comment'),
    path('product/<slug:product_slug>/comment/<str:comment_id>/hide/', interaction_views.hide_comment, name='hide_comment'),
    path('product/<slug:product_slug>/comment/<str:comment_id>/unhide/', interaction_views.unhide_comment, name='unhide_comment'),

    # ------------------------------------------------------- sales & payment (Tin)
    path('cart/', views.cart, name='cart'),
    path('checkout/', views.checkout, name='checkout'),
    path('tracking/', sales_views.track_order, name='tracking'),
    # JSON endpoints the checkout page posts to (CV52, CV53).
    path('checkout/place-order/', sales_views.place_order, name='place_order'),
    path('checkout/apply-coupon/', sales_views.apply_coupon, name='apply_coupon'),
    path('checkout/<str:order_code>/confirm-transfer/', sales_views.confirm_transfer,
         name='confirm_transfer'),

    # ---------------------------------------------------------------- admin
    # One /admin/... prefix for every module, so the shared admin menu in
    # Frontend/templates/admin/_admin_nav.html reads consistently. Tin's three
    # pages used to sit on their own /admin-dashboard/ style URLs outside it.
    path('admin/users/', accounts_views.admin_manage_user, name='admin_manage_user'),
    path('admin/users/<str:user_id>/lock/', accounts_views.admin_toggle_lock, name='admin_toggle_lock'),
    path('admin/users/<str:profile_id>/wholesale-review/', accounts_views.admin_wholesale_review, name='admin_wholesale_review'),

    # Catalogue admin (CV65-CV67). Each page renders once and then talks to
    # its own JSON endpoints below, which is why the fetch() URLs live under
    # the same /admin/ prefix as the page that calls them.
    path('admin/categories/', views.admin_categories, name='admin_categories'),
    path('admin/categories/data/', views.admin_categories_data, name='admin_categories_data'),
    path('admin/categories/create/', views.admin_category_create, name='admin_category_create'),
    path('admin/categories/<str:category_id>/update/', views.admin_category_update, name='admin_category_update'),
    path('admin/categories/<str:category_id>/hidden/', views.admin_category_hidden, name='admin_category_hidden'),
    path('admin/categories/<str:category_id>/delete/', views.admin_category_delete, name='admin_category_delete'),
    path('admin/categories/<str:category_id>/spec-template/', views.admin_category_spec_template, name='admin_category_spec_template'),
    path('admin/categories/<str:category_id>/spec-fields/create/', views.admin_category_spec_create, name='admin_category_spec_create'),
    path('admin/categories/<str:category_id>/spec-fields/<str:field_key>/update/', views.admin_category_spec_update, name='admin_category_spec_update'),
    path('admin/categories/<str:category_id>/spec-fields/<str:field_key>/delete/', views.admin_category_spec_delete, name='admin_category_spec_delete'),

    path('admin/products/', views.admin_products, name='admin_products'),
    path('admin/products/data/', views.admin_products_data, name='admin_products_data'),
    path('admin/products/create/', views.admin_product_create, name='admin_product_create'),
    path('admin/products/<str:product_id>/data/', views.admin_product_detail, name='admin_product_detail'),
    path('admin/products/<str:product_id>/update/', views.admin_product_update, name='admin_product_update'),
    path('admin/products/<str:product_id>/hidden/', views.admin_product_hidden, name='admin_product_hidden'),
    path('admin/products/<str:product_id>/variants/', views.admin_product_variants, name='admin_product_variants'),

    path('admin/inventory/', views.admin_inventory, name='admin_inventory'),
    path('admin/inventory/data/', views.admin_inventory_data, name='admin_inventory_data'),
    path('admin/inventory/low-stock/', views.admin_inventory_low_stock, name='admin_inventory_low_stock'),
    path('admin/inventory/adjust/', views.admin_inventory_adjust, name='admin_inventory_adjust'),
    path('admin/inventory/movements/', views.admin_inventory_movements, name='admin_inventory_movements'),

    # Content admin: news, customer feedback and review/comment moderation
    # (CV70, CV71).
    path('admin/news/', views.admin_news, name='admin_news'),
    path('admin/news/data/', views.admin_news_data, name='admin_news_data'),
    path('admin/news/create/', views.admin_news_create, name='admin_news_create'),
    path('admin/news/<str:news_id>/update/', views.admin_news_update, name='admin_news_update'),
    path('admin/news/<str:news_id>/hidden/', views.admin_news_hidden, name='admin_news_hidden'),
    path('admin/news/<str:news_id>/delete/', views.admin_news_delete, name='admin_news_delete'),

    path('admin/feedback/', views.admin_feedback, name='admin_feedback'),
    path('admin/feedback/data/', views.admin_feedback_data, name='admin_feedback_data'),
    path('admin/feedback/<str:feedback_id>/status/', views.admin_feedback_status, name='admin_feedback_status'),
    path('admin/feedback/<str:feedback_id>/reply/', views.admin_feedback_reply, name='admin_feedback_reply'),

    path('admin/moderation/', views.admin_moderation, name='admin_moderation'),
    path('admin/moderation/data/', views.admin_moderation_data, name='admin_moderation_data'),
    path('admin/moderation/reviews/<str:review_id>/hidden/', views.admin_moderation_review_hidden, name='admin_moderation_review_hidden'),
    path('admin/moderation/comments/<str:comment_id>/hidden/', views.admin_moderation_comment_hidden, name='admin_moderation_comment_hidden'),
    path('admin/moderation/comments/<str:comment_id>/reply/', views.admin_moderation_comment_reply, name='admin_moderation_comment_reply'),

    path('admin/dashboard/', sales_views.admin_dashboard, name='admin_dashboard'),
    path('admin/orders/', sales_views.admin_orders, name='admin_orders'),
    path('admin/orders/<str:order_id>/', sales_views.admin_order_detail, name='admin_order_detail'),
    path('admin/orders/<str:order_id>/status/', sales_views.admin_order_status, name='admin_order_status'),
    path('admin/promotions/', sales_views.admin_promotions, name='admin_promotions'),
    path('admin/promotions/<str:coupon_id>/toggle/', sales_views.admin_promotion_toggle, name='admin_promotion_toggle'),
    path('admin/promotions/<str:coupon_id>/delete/', sales_views.admin_promotion_delete, name='admin_promotion_delete'),

    # Old standalone URLs, kept so existing links and the team's bookmarks
    # still land on the merged pages instead of a 404.
    path('admin-dashboard/', RedirectView.as_view(pattern_name='admin_dashboard', permanent=False)),
    path('admin-orders/', RedirectView.as_view(pattern_name='admin_orders', permanent=False)),
    path('admin-promotions/', RedirectView.as_view(pattern_name='admin_promotions', permanent=False)),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
