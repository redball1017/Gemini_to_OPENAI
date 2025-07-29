from fastapi import FastAPI, Header, HTTPException, status
from typing import Annotated, Union, List, Literal, Optional
from pydantic import BaseModel, Field
import chat
from dotenv import load_dotenv
import time
load_dotenv()
app = FastAPI()
class ChatMessage(BaseModel):

    role: Literal["system", "user", "assistant"]
    content: str

# 这个模型对应整个JSON请求。 
# This model represents the entire JSON request.
class ChatCompletionRequest(BaseModel):
    model: str
    
    messages: List[ChatMessage]
    temperature: Optional[float] = Field(default=1.0, ge=0, le=2)

    stream: Optional[bool] = False

# Gemini API 请求模型
# Gemini API request model
class GeminiPart(BaseModel):
    text: str

class GeminiContent(BaseModel):
    role: Optional[str] = None
    parts: List[GeminiPart]

class GenerationConfig(BaseModel):
    temperature: Optional[float] = None
    max_output_tokens: Optional[int] = None
    top_p: Optional[float] = None

class GeminiChatRequest(BaseModel):

    contents: List[GeminiContent]
    system_instruction: Optional[GeminiContent] = None
    generation_config: Optional[GenerationConfig] = None
# Gemini API 响应模型
# Gemini API response model
class GeminiResponsePart(BaseModel):
    text: str

class GeminiResponseContent(BaseModel):
    parts: List[GeminiResponsePart]
    role: str

class GeminiCandidate(BaseModel):
    content: GeminiResponseContent
    finishReason: str

class UsageMetadata(BaseModel):
    promptTokenCount: int
    candidatesTokenCount: int
    totalTokenCount: int

class GeminiChatResponse(BaseModel):
    candidates: List[GeminiCandidate]
    usageMetadata: UsageMetadata

# --- OpenAI API 响应模型 ---
# --- OpenAI API response model ---
class OpenAIChoiceMessage(BaseModel):
    role: Literal["assistant"]
    content: str

class OpenAIChoice(BaseModel):
    index: int
    message: OpenAIChoiceMessage
    finish_reason: str

class OpenAIUsage(BaseModel):
    prompt_tokens: int
    completion_tokens: int
    total_tokens: int

class OpenAIChatCompletionResponse(BaseModel):
    id: str
    object: Literal["chat.completion"]
    created: int
    model: Optional[str] = None
    choices: List[OpenAIChoice]
    usage: OpenAIUsage

# --- OpenAI API getModels 响应模型 ---
# --- OpeAI API getModels response model ---
class OpenAIModelsData(BaseModel):
    id: str
    object: Optional[str] = "model"
    created: int
    owned_by: Optional[str] = "openai"
class OpenAIModel(BaseModel):
    object: str
    data: List[OpenAIModelsData]

# --- Gemini API getModels 响应模型 ---
# --- Gemini API getModels response model ---
class GeminiModelsData(BaseModel):
    name : str
    version : str
    display_name : Optional[str] = None
    description : Optional[str] = None
    inputTokenLimit : Optional[int] = None
    outputTokenLimit : Optional[int] = None
#    supportedGenerationMethods = Optional[List] = None
    thinking : Optional[bool] = None
    temperature : Optional[float] = None
    maxTemperature : Optional[float] = None
    topP : Optional[float] = None
    topK : Optional[int] = None
class GeminiModel(BaseModel):
    models: List[GeminiModelsData]

# 构建Gemini API 响应 转换为 OpenAI API 响应的函数
# Build a function that converts Gemini API responses to OpenAI API responses
def convert_gemini_to_openai(gemini_response, model) -> OpenAIChatCompletionResponse:

    openai_choices = []
    for candidate in gemini_response.candidates:
        content_text = "".join(part.text for part in candidate.content.parts)

        choice = OpenAIChoice(
            index=0,
            message=OpenAIChoiceMessage(
                role="assistant",
                content=content_text
            ),
            finish_reason=candidate.finishReason.lower()
        )
        openai_choices.append(choice)
        usage = OpenAIUsage(
            prompt_tokens=gemini_response.usageMetadata.promptTokenCount,
            completion_tokens=gemini_response.usageMetadata.candidatesTokenCount,
            total_tokens=gemini_response.usageMetadata.totalTokenCount
        )
        openai_response = OpenAIChatCompletionResponse(
            id=f"chatcmpl-{int(time.time())}", # 创建一个模拟的ID. Create a fake ID.
            object="chat.completion",
            created=int(time.time()),
            choices=openai_choices,
            usage=usage
        )
        return openai_response
def gemini_getModel_to_OPENAI(gemini_response) -> OpenAIModel:
    OpenAIModelsDataRaw = []
    for GeminiModel in gemini_response.models:
        OpenAIModelsDataRaw.append(OpenAIModelsData(
            id=GeminiModel.name.replace("models/", ""),
            object="model",
            created=int(time.time()),
            owned_by="openai"
        ))
    return OpenAIModel(
        object= "list",
        data=OpenAIModelsDataRaw
    )
    
@app.post("/v1/chat/completions")
async def chat_completions(openai_request: ChatCompletionRequest):
    gemini_contents = []
    system_instruction = None
    for message in openai_request.messages: # 遍历请求中的消息 Traverse the messages in the request
        if message.role == "system":
            system_instruction = GeminiContent(role= None, parts=[GeminiPart(text=message.content)]) # 如果为系统消息，则创建系统提示的GeminiContent. If the message is a system message, create a GeminiContent for the system prompt
            continue
        elif message.role == "user": # 如果为用户消息，则创建用户消息的GeminiContent. If the message is a user message, create a GeminiContent for the user message
            gemini_role = "user"
        elif message.role == "assistant": # 如果为assistant消息，则创建model消息的GeminiContent. if the message is an assistant message, create a GeminiContent for the model message
            gemini_role = "model"
        else:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid role") # 如果消息的角色不在预设的角色中，则返回400错误 If the role of the message is not in the pre-set role, return a 400 error
        gemini_contents.append(GeminiContent(
            role=gemini_role,
            parts=[GeminiPart(text=message.content)]
        ))
    generation_config = GenerationConfig( # 创建生成配置 Create generation configuration
        temperature=openai_request.temperature,
        max_output_tokens=None,
        top_p=None
    )
    gemini_request = GeminiChatRequest( # 创建Gemini请求 Create Gemini request
        contents=gemini_contents,
        system_instruction=system_instruction,
        generation_config=generation_config
    )
    gemini_request_json = gemini_request.model_dump_json(exclude_none=True) # 序列化Gemini请求为JSON字符串，忽略空值 Serialize Gemini request to JSON string, ignore empty values
    #print(gemini_request_json)
    response, status_code = chat.send_request(gemini_request=gemini_request_json,model=openai_request.model) # 调用Gemini API.Use Gemini API.
    #print(gemini_response_raw)
    if status_code != 200:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Gemini API error" + str(response)) # 如果Gemini API返回错误，则返回500错误. If Gemini API returns an error, return a 500 error.
    else:
        gemini_response = GeminiChatResponse.model_validate(response,strict=False) # 反序列化Gemini响应为GeminiChatResponse模型，忽略非法字段. Deserialize Gemini response to GeminiChatResponse model, ignore invalid fields.
        converted_response = convert_gemini_to_openai(gemini_response,model=openai_request.model) # 转换Gemini响应为OpenAI响应. Convert Gemini response to OpenAI response.
    #print(converted_response.model_dump_json(exclude_none=True))
        return converted_response
@app.get("/v1/models")
def get_models():
    raw_response = chat.getModel()
    gemini_response = GeminiModel.model_validate(raw_response) # 反序列化Gemini响应为GeminiModel模型，忽略非法字段
    getModels_response = gemini_getModel_to_OPENAI(gemini_response) # 转换Gemini响应为OpenAI响应
    return getModels_response

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
