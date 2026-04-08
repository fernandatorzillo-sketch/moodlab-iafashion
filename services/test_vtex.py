from data_models.integracao import VtexClient

client = VtexClient(
    account_name="lojaaguadecoco",
    environment="vtexcommercestable",
    app_key="vtexappkey-lojaaguadecoco-PNVBLD",
    app_token="QHSZNPXVZKBDVWPBEIEXMJFDPZNQNHMKBUXNLYBRJNQOMNDTPTHNUCDKMWOKRFEJLUUEHUCAJNAXGPHKXNRASYAKXUIBGJREVNYHCFRLDBKUIUKFPSXZIUJOSMRVWEXP"
)

resultado = client.get_products()
print(resultado["url"])
print(resultado["status_code"])
print(resultado["body"])