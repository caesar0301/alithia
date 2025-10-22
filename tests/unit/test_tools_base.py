from alithia.core.tools import BaseTool, ToolInput, ToolOutput


class EchoInput(ToolInput):
    text: str


class EchoOutput(ToolOutput):
    text: str


class EchoTool(BaseTool):
    name: str = "test.echo"
    description: str = "Echo back provided text"
    args_schema: type[EchoInput] = EchoInput

    def execute(self, inputs: EchoInput, **kwargs):
        return EchoOutput(text=inputs.text)

    def _run(self, text: str) -> EchoOutput:  # type: ignore[override]
        return self.execute(EchoInput(text=text))


def test_tool_execute_and_invoke():
    tool = EchoTool()
    out = tool.execute(EchoInput(text="hello"))
    assert out.text == "hello"
    out2 = tool.invoke({"text": "world"})
    assert out2.text == "world"
