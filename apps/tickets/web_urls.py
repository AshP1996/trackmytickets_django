from django.urls import path
from apps.core.web_views import RenderTemplateView

urlpatterns = [
    path('tickets', RenderTemplateView.as_view(template_name='tickets/list.html'), name='tickets_list'),
    path('tickets/create', RenderTemplateView.as_view(template_name='tickets/create.html'), name='ticket_create'),
    path('tickets/<str:ticket_id>', RenderTemplateView.as_view(template_name='tickets/details.html'), name='ticket_detail'), # Supports ID or Key in JS
    
    path('projects', RenderTemplateView.as_view(template_name='projects/list.html'), name='projects_list'),
    path('projects/<int:project_id>', RenderTemplateView.as_view(template_name='projects/detail.html'), name='project_detail'),
    path('projects/<int:project_id>/analytics', RenderTemplateView.as_view(template_name='projects/analytics.html'), name='project_analytics'),
    
    # Knowledge Base
    path('knowledge-base', RenderTemplateView.as_view(template_name='knowledge_base/index.html'), name='knowledge_base'),
    path('knowledge-base/<int:article_id>', RenderTemplateView.as_view(template_name='knowledge_base/article.html'), name='kb_article'),
]
