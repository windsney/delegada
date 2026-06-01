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
    POSTOS_GRADUACOES = [
        ('SD PM', 'Sd PM'),
        ('CB PM', 'Cb PM'),
        ('3SGT PM', '3º Sgt PM'),
        ('2SGT PM', '2º Sgt PM'),
        ('1SGT PM', '1º Sgt PM'),
        ('SUB TEN PM', 'Sub Ten PM'),
        ('ASP OF PM', 'Asp Of PM'),
        ('2TEN PM', '2º Ten PM'),
        ('1TEN PM', '1º Ten PM'),
        ('CAP PM', 'Cap PM'),
        ('MAJ PM', 'Maj PM'),
        ('TEN CEL PM', 'Ten Cel PM'),
        ('CEL PM', 'Cel PM'),
    ]

    nome_guerra = models.CharField(max_length=100, verbose_name="Nome de Guerra (Ex: Cb José)")
    categoria = models.CharField(max_length=10, choices=ValorHoraCategoria.CATEGORIAS, verbose_name="Categoria para Pagamento")
    
    # Novos Campos Obrigatórios
    rgpm = models.CharField(max_length=20, unique=True, verbose_name="RGPM")
    cpf = models.CharField(max_length=14, unique=True, verbose_name="CPF")
    posto_graduacao = models.CharField(max_length=20, choices=POSTOS_GRADUACOES, verbose_name="Posto / Graduação")
    endereco = models.CharField(max_length=255, verbose_name="Endereço")
    filiacao = models.CharField(max_length=255, verbose_name="Filiação (Mãe/Pai)")
    naturalidade = models.CharField(max_length=100, verbose_name="Naturalidade")
    data_nascimento = models.DateField(verbose_name="Data de Nascimento")
    
    # Novos Campos Não Obrigatórios (blank=True, null=True)
    agencia = models.CharField(max_length=20, blank=True, null=True, verbose_name="Agência Bancária")
    conta_corrente = models.CharField(max_length=30, blank=True, null=True, verbose_name="Conta Corrente")
    telefone = models.CharField(max_length=20, blank=True, null=True, verbose_name="Telefone")
    email = models.EmailField(blank=True, null=True, verbose_name="E-mail")

    def __str__(self):
        return f"{self.get_posto_graduacao_display()} {self.nome_guerra}"
    
    class Meta:
        ordering = ['nome_guerra']

class PontoFixo(models.Model):
    nome = models.CharField(max_length=100, unique=True, verbose_name="Nome do Ponto Fixo")
    localizacao = models.CharField(max_length=255, verbose_name="Endereço/Localização")
    comentario = models.TextField(
        blank=True, 
        null=True, 
        verbose_name="Orientação para a Guarnição"
    )

    def __str__(self):
        return self.nome

class EscalaDiaria(models.Model):
    data = models.DateField(unique=True, verbose_name="Data do Policiamento")

    def __str__(self):
        return f"Escala Diária - {self.data.strftime('%d/%m/%Y')}"

class CartaoPoliciamento(models.Model):
    escala = models.ForeignKey(EscalaDiaria, on_delete=models.CASCADE, related_name="cartoes")
    ponto_fixo = models.ForeignKey(PontoFixo, on_delete=models.CASCADE, verbose_name="Ponto Fixo")
    
    # O HORÁRIO AGORA FICA AQUI (Individual por guarnição)
    horario_inicio = models.TimeField(verbose_name="Hora Início", default="19:00")
    horario_fim = models.TimeField(verbose_name="Hora Fim", default="01:00")
    
    comandante = models.ForeignKey(Policial, on_delete=models.SET_NULL, null=True, blank=True, related_name="como_comandante")
    motorista = models.ForeignKey(Policial, on_delete=models.SET_NULL, null=True, blank=True, related_name="como_motorista")
    patrulheiro = models.ForeignKey(Policial, on_delete=models.SET_NULL, null=True, blank=True, related_name="como_patrulheiro")

    def __str__(self):
        return f"{self.ponto_fixo.nome} ({self.horario_inicio} - {self.horario_fim})"

    @property
    def total_horas(self):
        """Calcula a quantidade de horas trabalhadas nesta guarnição específica"""
        import datetime
        data_dummy = datetime.date.today()
        dt_inicio = datetime.datetime.combine(data_dummy, self.horario_inicio)
        dt_fim = datetime.datetime.combine(data_dummy, self.horario_fim)
        
        if dt_fim <= dt_inicio:
            dt_fim += datetime.timedelta(days=1)
            
        diferenca = dt_fim - dt_inicio
        return diferenca.total_seconds() / 3600

    def calcular_custo_cartao(self):
        """Calcula o valor baseado nas horas desta guarnição e na categoria dos PMs"""
        horas = self.total_horas
        valores = {v.categoria: v.valor_por_hora for v in ValorHoraCategoria.objects.all()}
        
        total = 0
        for pm in [self.comandante, self.motorista, self.patrulheiro]:
            if pm and pm.categoria in valores:
                total += float(valores[pm.categoria]) * horas
        return total