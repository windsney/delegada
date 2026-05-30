from django.urls import path
from .views import HomeView

urlpatterns = [
    #path('', views.home, name='home'),
    #path('sobre/', views.sobre, name='sobre'),
    #path('contato/', views.contato, name='contato'),
# CBV básica
    #path('minhaview/', MinhaView.as_view(), name='minha-view'),
    
    # TemplateView
    path('', HomeView.as_view(), name='home'),
    
    # ListView
    #path('itens/', ListaItensView.as_view(), name='lista-itens'),
    
    # DetailView com parâmetro na URL
    #path('item/<int:pk>/', DetalheItemView.as_view(), name='detalhe-item'),

]
