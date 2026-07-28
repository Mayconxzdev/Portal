# LEGACY_PURCHASES_IMPORT_PREVIEW_SAMPLE.md

```json
{
  "suppliers_sample": [
    {
      "name": "Fornecedor Alfa Ltda",
      "cnpj_cpf_raw": "11111111000111",
      "cnpj_cpf_normalized": "11111111000111",
      "cnpj_cpf_masked": "72.***.***/0001-10",
      "contact": "Contato Alfa",
      "email_raw": "vendas@fornecedor-alfa.example",
      "email_normalized": "vendas@fornecedor-alfa.example",
      "email_masked": "v****s@fornecedor-hardware.example",
      "phone_masked": "(08) ****-3355",
      "city": "Eldorado do Sul",
      "uf": "RS"
    },
    {
      "name": "Fornecedor Beta Ltda",
      "cnpj_cpf_raw": "22222222000122",
      "cnpj_cpf_normalized": "22222222000122",
      "cnpj_cpf_masked": "07.***.***/0001-09",
      "contact": "Contato Beta",
      "email_raw": "contato@fornecedor-beta.example",
      "email_normalized": "contato@fornecedor-beta.example",
      "email_masked": "c*********o@fornecedor-hardware.example",
      "phone_masked": "(11) ****-8000",
      "city": "São Paulo",
      "uf": "SP"
    },
    {
      "name": "Fornecedor Gama Ltda",
      "cnpj_cpf_raw": "33333333000133",
      "cnpj_cpf_normalized": "33333333000133",
      "cnpj_cpf_masked": "12.***.***/0001-99",
      "contact": "Contato Gama",
      "email_raw": "contato@fornecedor-gama.example",
      "email_normalized": "contato@fornecedor-gama.example",
      "email_masked": "c****s@fornecedor-gama.example",
      "phone_masked": "(11) ****-8888",
      "city": "Campinas",
      "uf": "SP"
    },
    {
      "name": "Fornecedor Delta Ltda",
      "cnpj_cpf_raw": "44444444000144",
      "cnpj_cpf_normalized": "44444444000144",
      "cnpj_cpf_masked": "98.***.***/0001-88",
      "contact": "Bianca Metal",
      "email_raw": "contato@fornecedor-delta.example",
      "email_normalized": "contato@fornecedor-delta.example",
      "email_masked": "c*****o@fornecedor-delta.example",
      "phone_masked": "(11) ****-4444",
      "city": "São Bernardo",
      "uf": "SP"
    },
    {
      "name": "Fornecedor Delta Filial",
      "cnpj_cpf_raw": "44444444000144",
      "cnpj_cpf_normalized": "44444444000144",
      "cnpj_cpf_masked": "98.***.***/0001-88",
      "contact": "João Filial",
      "email_raw": "filial@fornecedor-delta.example",
      "email_normalized": "filial@fornecedor-delta.example",
      "email_masked": "v****s@fornecedor-delta.example",
      "phone_masked": "(11) ****-4445",
      "city": "São Bernardo",
      "uf": "SP"
    }
  ],
  "items_sample": [
    {
      "sku": "CHP-001",
      "name": "Chapa Fina Frio 0,60mm 2x1m",
      "measure": "2 x 1 m",
      "thickness": "0,60 mm",
      "category": "Chapas",
      "price_reference": 150.0,
      "price_last_buy": 145.0,
      "last_buy_date": "2026-05-10"
    },
    {
      "sku": "CHP-002",
      "name": "Chapa Fina Quente 2,00mm 2x1m",
      "measure": "2 x 1 m",
      "thickness": "2,00 mm",
      "category": "Chapas",
      "price_reference": 280.0,
      "price_last_buy": 295.0,
      "last_buy_date": "2026-05-12"
    },
    {
      "sku": "TB-001",
      "name": "Tubo Inox 304 2\" x 1.5mm 6m",
      "measure": "6 m",
      "thickness": "1,50 mm",
      "category": "Chapa e Tubo Inox",
      "price_reference": 450.0,
      "price_last_buy": 450.0,
      "last_buy_date": "2026-05-15"
    },
    {
      "sku": "CNT-001",
      "name": "Cantoneira Inox 1\" x 1/8\" 6m",
      "measure": "6 m",
      "thickness": "3,18 mm",
      "category": "Cantoneira Inox",
      "price_reference": 180.0,
      "price_last_buy": 175.0,
      "last_buy_date": "2026-05-18"
    },
    {
      "sku": "BC-001",
      "name": "Barra Chata Inox 2\" x 1/4\" 6m",
      "measure": "6 m",
      "thickness": "6,35 mm",
      "category": "Barra Chata Inox",
      "price_reference": 220.0,
      "price_last_buy": 230.0,
      "last_buy_date": "2026-05-20"
    }
  ],
  "quotes_sample": [
    {
      "date": "2026-05-10",
      "rfq_id": "RFQ-CPD-01",
      "sku": "CHP-001",
      "material_name": "Chapa Fina Frio 0,60mm 2x1m",
      "supplier_name": "Fornecedor Gama Ltda",
      "unit_price": 145.0,
      "variation": -3.3,
      "payment_terms": "Boleto 30 dias",
      "delivery_days": 5,
      "approved_by": "wilson",
      "evidence": "proposta_chapa_01.pdf"
    },
    {
      "date": "2026-05-12",
      "rfq_id": "RFQ-CPD-02",
      "sku": "CHP-002",
      "material_name": "Chapa Fina Quente 2,00mm 2x1m",
      "supplier_name": "Fornecedor Delta Ltda",
      "unit_price": 295.0,
      "variation": 0.053,
      "payment_terms": "Boleto 45 dias",
      "delivery_days": 7,
      "approved_by": "wilson",
      "evidence": "proposta_chapa_02.pdf"
    },
    {
      "date": "2026-05-15",
      "rfq_id": "RFQ-CPD-03",
      "sku": "TB-001",
      "material_name": "Tubo Inox 304 2\" x 1.5mm 6m",
      "supplier_name": "Fornecedor Gama Ltda",
      "unit_price": 450.0,
      "variation": 0.0,
      "payment_terms": "Boleto 30 dias",
      "delivery_days": 3,
      "approved_by": "wilson",
      "evidence": "proposta_tubo_01.pdf"
    }
  ],
  "duplicates_detected": [
    {
      "type": "CNPJ/CPF Duplicado",
      "key": "44444444000144",
      "items": [
        {
          "name": "Fornecedor Delta Ltda",
          "cnpj_cpf_masked": "98.***.***/0001-88",
          "email_masked": "c*****o@fornecedor-delta.example"
        },
        {
          "name": "Fornecedor Delta Filial",
          "cnpj_cpf_masked": "98.***.***/0001-88",
          "email_masked": "v****s@fornecedor-delta.example"
        }
      ]
    }
  ]
}
```
