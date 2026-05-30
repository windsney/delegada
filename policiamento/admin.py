from django.contrib import admin



from .models import PontoFixo, EscalaDiaria, CartaoPoliciamento, Policial, ValorHoraCategoria

admin.site.register(Policial)
admin.site.register(ValorHoraCategoria)
admin.site.register(PontoFixo)
admin.site.register(EscalaDiaria)
admin.site.register(CartaoPoliciamento)
