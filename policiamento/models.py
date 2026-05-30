from django.db import models

class ValorHoraCategoria(models.Model):
    CATEGORIAS = [
        ('SD_CB', 'Soldado / Cabo'),
        ('SGT_SUB', 'Sargento / Subtenente'),
        ('OFI', 'Oficiais'),
    ]
    categoria = models.CharField(max_length=10, choices=CATEGORIAS, unique=True, verbose_name="Categoria")
    valor_por_hora = models.DecimalField(max_digits=6, decimal_places=2, verbose_name="Valor por Hora (R$)")

    def __str__(self):
        return f"{self.get_categoria_display()} - R$ {self.valor_por_hora}/h"

class Policial(models.Model):
    nome_guerra = models.CharField(max_length=100, verbose_name="Nome de Guerra (Ex: Cb José)")
    categoria = models.CharField(max_length=10, choices=ValorHoraCategoria.CATEGORIAS, verbose_name="Categoria para Pagamento")

    def __str__(self):
        return self.nome_guerra
    
    class Meta:
        ordering = ['nome_guerra']

class PontoFixo(models.Model):
    nome = models.CharField(max_length=100, unique=True, verbose_name="Nome do Ponto Fixo")
    localizacao = models.CharField(max_length=255, verbose_name="Endereço/Localização")

    def __str__(self):
        return self.nome

class EscalaDiaria(models.Model):
    data = models.DateField(verbose_name="Data do Policiamento")
    horario_inicio = models.TimeField(verbose_name="Hora Início")
    horario_fim = models.TimeField(verbose_name="Hora Fim")

    def __str__(self):
        return f"Escala {self.data.strftime('%d/%m/%Y')} ({self.horario_inicio} às {self.horario_fim})"

    @property
    def total_horas(self):
        """Calcula a quantidade de horas do turno"""
        import datetime
        # Converte para datetime para calcular a diferença (trata virada de dia)
        data_dummy = datetime.date.today()
        dt_inicio = datetime.datetime.combine(data_dummy, self.horario_inicio)
        dt_fim = datetime.datetime.combine(data_dummy, self.horario_fim)
        
        if dt_fim <= dt_inicio:
            dt_fim += datetime.timedelta(days=1)
            
        diferenca = dt_fim - dt_inicio
        return diferenca.total_seconds() / 3600

class CartaoPoliciamento(models.Model):
    escala = models.ForeignKey(EscalaDiaria, on_delete=models.CASCADE, related_name="cartoes")
    ponto_fixo = models.ForeignKey(PontoFixo, on_delete=models.CASCADE, verbose_name="Ponto Fixo")
    comandante = models.ForeignKey(Policial, on_delete=models.SET_NULL, null=True, blank=True, related_name="como_comandante")
    motorista = models.ForeignKey(Policial, on_delete=models.SET_NULL, null=True, blank=True, related_name="como_motorista")
    patrulheiro = models.ForeignKey(Policial, on_delete=models.SET_NULL, null=True, blank=True, related_name="como_patrulheiro")

    def __str__(self):
        return f"{self.ponto_fixo.nome} - {self.escala.data}"

    def calcular_custo_cartao(self):
        """Calcula o valor total gasto nesta guarnição baseado nas categorias dos policiais"""
        horas = self.escala.total_horas
        valores = {v.categoria: v.valor_por_hora for v in ValorHoraCategoria.objects.all()}
        
        total = 0
        for pm in [self.comandante, self.motorista, self.patrulheiro]:
            if pm and pm.categoria in valores:
                total += float(valores[pm.categoria]) * horas
        return total