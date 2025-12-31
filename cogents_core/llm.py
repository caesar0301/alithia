class BaseLLMClient:
    pass
def get_llm_client(*args, **kwargs):
    return BaseLLMClient()
