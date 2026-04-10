@router.post("/lookup")
def lookup_customer_closet(payload: LookupRequest):
    try:
        email = normalize_email(payload.email)

        if not email:
            raise HTTPException(status_code=400, detail="E-mail é obrigatório")

        closet_data = get_customer_closet(email)
        closet_products = closet_data.get("closet_products", [])

        customer = {
            "name": email.split("@")[0],
            "email": email,
        }

        return {
            "customer": customer,
            "closet": closet_products,
            "looks": [],
            "recommendations": [],
            "debug": {
                "email_input": payload.email,
                "email_normalized": email,
                "pedidos_count": closet_data["total_pedidos"],
                "closet_final_count": len(closet_products),
            },
        }

    except HTTPException:
        raise
    except Exception as e:
        print("🔥 ERRO REAL NO LOOKUP:")
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))