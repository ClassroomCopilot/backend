from dotenv import load_dotenv, find_dotenv
load_dotenv(find_dotenv())
import os
import modules.logger_tool as logger
log_name = 'api_modules_interactive_langgraph_query'
log_dir = os.getenv("LOG_PATH", "/logs")  # Default path as fallback
logging = logger.get_logger(
    name=log_name,
    log_level=os.getenv("LOG_LEVEL", "DEBUG"),
    log_path=log_dir,
    log_file=log_name,
    runtime=True,
    log_format='default'
)
from langchain_core.messages import BaseMessage, HumanMessage
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from typing import Annotated, Sequence, List, TypedDict
from langchain_core.pydantic_v1 import BaseModel, Field
import operator
from langchain_openai import ChatOpenAI
import openai
import aiohttp
from urllib.parse import urlencode
from bs4 import BeautifulSoup
import asyncio
import re
from datetime import datetime
from extruct import extract
from w3lib.html import get_base_url
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
from modules.redis_config import get_cached_results, set_cached_results

# Explicitly set the OpenAI API key
openai_api_key = os.getenv("OPENAI_API_KEY")
if not openai_api_key or openai_api_key.lower() == "null":
    raise ValueError("OPENAI_API_KEY is not set or is set to NULL in the environment variables")

openai.api_key = openai_api_key
logging.info(f"OpenAI API Key: {openai_api_key[:5]}...{openai_api_key[-5:]}")

from langgraph.constants import END, Send
from langgraph.graph import StateGraph
from langgraph.checkpoint.memory import MemorySaver

simple_model = ChatOpenAI(model="gpt-3.5-turbo", temperature=0, streaming=True)
advanced_model = ChatOpenAI(model="gpt-4o", temperature=0, streaming=True)

class Queries(BaseModel):
    """List of search queries"""
    queries: List[str] = Field(
        description="List of the generated search queries"
    )

class SummaryState(TypedDict):
    content: str
    query: str

class PerplexityClone:
    ADDITIONAL_QUESTION_PROMPT = """You are tasked with analyzing a message to determine if it requires additional input from the user.
    Your goal is to be conservative in asking for additional input, only indicating that more information is needed if it is relevant to answering the question or fulfilling the request in the message.
    Use the following criteria to guide your decision:
    - Is the core question or request clearly stated?
    - Are all necessary details provided to understand the context?
    - Would additional information significantly change or improve the response?
    - Is the missing information essential or helpful?

    Before giving your final answer, think through your analysis in a scratchpad:

    <scratchpad>
    Analyze the message here, considering the criteria above. Think step-by-step about whether additional input is truly necessary or if the message can be responded to with the given information.
    </scratchpad>

    After your analysis, provide your final answer in the following format:

    <answer>
    [YES/NO]: (Choose YES if additional input is required, NO if it is not)
    Justification: (Briefly explain your reasoning)
    </answer>
    Remember to be conservative in asking for additional input. Only say YES if the additional information is highly relevant and necessary to properly address the message."""

    SEARCH_QUERY_PROMPT = """You are a helpful AI assistant, create a list of 2-3 search queries based on the message"""

    FINAL_NODE_SYSTEM_PROMPT = """You are a helpful AI assistant, answer the given question based on the context. Clearly cite the sources for your answer including the links for the sources next to each point"""

    FINAL_NODE_PROMPT = """Question: {question}
    Context: {context}
    Answer:"""

    @staticmethod
    def prioritize_content(extracted_text, query):
        """Prioritize content based on relevance to the query."""
        documents = [extracted_text, query]
        tfidf_vectorizer = TfidfVectorizer().fit_transform(documents)
        cosine_matrix = cosine_similarity(tfidf_vectorizer[0:1], tfidf_vectorizer)
        score = cosine_matrix[0][1]  # Similarity score with the query
        logging.debug(f"Content prioritization score: {score}")
        return score
        
    # Define OverallState with class methods for graph nodes
    class OverallState(TypedDict):
        messages: Annotated[Sequence[BaseMessage], operator.add]
        next: str
        search_queries: list[str]
        search_results: list[str]
        page_content: list[str]
        page_summaries: Annotated[list, operator.add]
        needs_more_info: bool = False

        @classmethod
        def additional_questions_node(cls, state):
            logging.debug("Entering additional_questions_node")
            messages = state['messages']
            last_message = messages[-1]

            prompt = ChatPromptTemplate.from_messages(
                [
                    ("system", PerplexityClone.ADDITIONAL_QUESTION_PROMPT),
                    MessagesPlaceholder(variable_name="messages"),
                    MessagesPlaceholder(variable_name="agent_scratchpad")
                ]
            )
            chain = prompt | simple_model
            input_data = {
                "messages": messages,
                "agent_scratchpad": []
            }
            logging.chat(f"additional_questions_node is sending data to model: {input_data}")
            result = chain.invoke(input_data)
            logging.chat(f"additional_questions_node received data from model: {result.content}")
            needs_more_info = "YES" in result.content.upper()
            return {"next": result.content, "needs_more_info": needs_more_info}

        @classmethod
        def where_to_go(cls, state):
            next = state['next']
            if "NO" in next:
                return "proceed"
            else:
                return "ask"

        @classmethod
        def ask_node(cls, state):
            messages = state['messages']
            user_question = messages[0]

            prompt = f"Ask any additional questions that are required to answer the question: {user_question.content}"
            logging.chat(f"ask_node is sending data to model: {prompt}")
            question = simple_model.invoke(prompt)
            logging.chat(f"ask_node received data from model: {question.content}")
            return {"messages": [question]}

        @classmethod
        def new_question_node(cls, state):
            messages = state['messages']
            initial_question = messages[0]

            prompt = f"Reframe the initial question: {initial_question.content} based on the messages: {messages}"
            logging.chat(f"new_question_node is sending data to model: {prompt}")
            response = simple_model.invoke(prompt)
            logging.chat(f"new_question_node received data from model: {response.content}")
            new_question = HumanMessage(content=response.content)
            return {"messages": [new_question]}

        @classmethod
        def search_query_node(cls, state):
            messages = state['messages']
            last_message = messages[-1]

            prompt = ChatPromptTemplate.from_messages(
                [
                    ("system", PerplexityClone.SEARCH_QUERY_PROMPT),
                    MessagesPlaceholder(variable_name="messages"),
                ]
            )
            chain = prompt | simple_model
            logging.chat(f"search_query_node is sending data to model: {messages}")
            result = chain.invoke(messages)
            logging.chat(f"search_query_node received data from model: {result.content}")

            queries = [q.strip() for q in result.content.split('\n') if q.strip()]
            return {"search_queries": queries}

        @classmethod
        async def search_results_node(cls, state):
            logging.debug("Entering search_results_node")
            queries = state['search_queries']
            logging.debug(f"Queries: {queries}")
            try:
                results = await cls.search(queries)
                logging.debug(f"Search results: {results}")
            except Exception as e:
                logging.error(f"Error in search_results_node: {str(e)}")
                raise
            return {"search_results": results}

        @classmethod
        async def web_scrape_node(cls, state):
            logging.debug("Entering web_scrape_node")
            search_results = state['search_results']
            crawled_results = []

            logging.debug(f"Search results: {search_results}")
            for result_list in search_results:
                for result in result_list:
                    logging.debug(f"Result: {result}")
                    url = result.get('url', 'No URL')
                    content = result.get('content', result.get('title', 'No content'))
                    logging.debug(f"Using crawler on: {url} with content: {content}")
                    
                    try:
                        crawled_content = await cls.crawl_page(result, state['messages'][-1].content, retries=3, timeout=20)
                        if crawled_content:
                            logging.debug(f"Crawled content: {crawled_content}")
                            crawled_results.append(crawled_content)
                        else:
                            logging.error(f"No content found for {url}")
                    except Exception as e:
                        logging.error(f"Error crawling {url}: {str(e)}")
            
            if not crawled_results:
                logging.error("No crawled results found")
                return {"page_content": [{"page_content": "No relevant content found.", "metadata": {}}]}  # Adjusted to ensure it returns a dictionary
            else:
                logging.debug(f"Crawled results: {crawled_results}")
                return {"page_content": [{"page_content": cr['content'], "metadata": {"source": cr['url']}} for cr in crawled_results]}
        
        @classmethod
        async def crawl_page(cls, result, query, retries=3, timeout=20):
            """Crawl a page with retries and timeouts."""
            for attempt in range(retries):
                try:
                    async with aiohttp.ClientSession() as session:
                        async with session.get(result['url'], timeout=timeout) as response:
                            if response.status != 200:
                                raise Exception(f"HTTP status {response.status}")
                            html = await response.text()

                    # Extract structured data
                    structured_data = await cls.extract_structured_data(html, result['url'])
                    if structured_data:
                        logging.debug(f"Structured data extracted: {structured_data}")
                    else:
                        logging.debug("No structured data found")

                    soup = BeautifulSoup(html, 'html.parser')

                    # Remove unnecessary elements
                    for element in soup(['script', 'style', 'nav', 'header', 'footer']):
                        element.decompose()

                    main_content = (
                        soup.find('main') or
                        soup.find('article') or
                        soup.find('.content') or
                        soup.find(id='content') or
                        soup.body
                    )

                    if main_content:
                        # Prioritize specific content elements
                        priority_elements = main_content.find_all(['h1', 'h2', 'h3', 'p'])
                        extracted_text = '\n\n'.join(el.get_text().strip() for el in priority_elements if el.get_text().strip())

                        # If not enough content, fall back to other elements
                        if len(extracted_text) < 500:
                            content_elements = main_content.find_all(['h4', 'h5', 'h6', 'li', 'td', 'th', 'blockquote', 'pre', 'code'])
                            extracted_text += '\n\n' + '\n\n'.join(el.get_text().strip() for el in content_elements if el.get_text().strip())

                        # Prioritize the extracted content based on relevance to the query
                        relevance_score = PerplexityClone.prioritize_content(extracted_text, query)
                        logging.debug(f"Content relevance score: {relevance_score}")

                        # Extract metadata
                        meta_description = soup.find('meta', attrs={'name': 'description'})
                        meta_keywords = soup.find('meta', attrs={'name': 'keywords'})
                        og_title = soup.find('meta', property='og:title')
                        og_description = soup.find('meta', property='og:description')

                        # Combine metadata with extracted text
                        metadata = [
                            result['title'],
                            og_title['content'] if og_title else '',
                            meta_description['content'] if meta_description else '',
                            og_description['content'] if og_description else '',
                            meta_keywords['content'] if meta_keywords else '',
                        ]
                        extracted_text = '\n\n'.join(filter(None, metadata + [extracted_text]))

                        # Limit the extracted text to 10000 characters
                        extracted_text = extracted_text[:10000]

                        # Highlight query terms in the content
                        highlighted_content = cls.highlight_query_terms(extracted_text, query)

                        # Extract publication date
                        published_date = cls.extract_publication_date(soup)

                        return {
                            'title': result['title'],
                            'url': result['url'],
                            'content': highlighted_content,
                            'structured_data': structured_data,
                            'relevance_score': relevance_score,
                            'publishedDate': published_date.isoformat() if published_date else None
                        }
                    else:
                        logging.debug("No main content found")

                except asyncio.TimeoutError:
                    logging.warning(f"Timeout occurred while crawling {result['url']}. Attempt {attempt + 1} of {retries}")
                except Exception as error:
                    logging.error(f"Error crawling {result['url']}: {str(error)}. Attempt {attempt + 1} of {retries}")

            # If all retries fail, return a default response
            logging.debug("All retries failed. Returning default response.")
            return {
                'title': result['title'],
                'url': result['url'],
                'content': result.get('content', 'Content unavailable due to crawling error.'),
                'structured_data': None,
                'relevance_score': None,
                'publishedDate': None
            }

        @staticmethod
        async def extract_structured_data(html, url):
            """Extract structured data (e.g., JSON-LD) from a webpage."""
            logging.debug(f"Extracting structured data from: {url}")
            base_url = get_base_url(html, url)
            data = extract(html, base_url=base_url)
            logging.debug(f"Structured data extracted: {data}")
            return data

        @staticmethod
        def highlight_query_terms(text, query):
            words = query.lower().split()
            for word in words:
                pattern = re.compile(r'\b' + re.escape(word) + r'\b', re.IGNORECASE)
                text = pattern.sub(f'**{word.upper()}**', text)
            logging.debug(f"Highlighted text: {text}")
            return text

        @staticmethod
        def extract_publication_date(soup):
            date_meta = soup.find('meta', property='article:published_time')
            if date_meta:
                logging.debug(f"Extracted publication date: {date_meta['content']}")
                return datetime.fromisoformat(date_meta['content'].split('+')[0])

            date_meta = soup.find('meta', attrs={'name': 'pubdate'})
            if date_meta:
                logging.debug(f"Extracted publication date: {date_meta['content']}")
                return datetime.fromisoformat(date_meta['content'].split('+')[0])

            date_tag = soup.find(['time', 'span'], attrs={'datetime': True})
            if date_tag:
                logging.debug(f"Extracted publication date: {date_tag['datetime']}")
                return datetime.fromisoformat(date_tag['datetime'].split('+')[0])

            return None

        @classmethod
        def generate_summary(cls, state: SummaryState):
            content_item = state['content']
            logging.debug(f"Content item received in generate_summary: {content_item} (type: {type(content_item)})")
            
            if isinstance(content_item, dict):
                logging.debug(f"Content item is a dictionary: {content_item}")
                content = content_item.get('page_content', '')
                source = content_item.get('metadata', {}).get('source', 'Unknown Source')
            else:
                logging.error(f"Expected a dictionary for content_item but got {type(content_item)}: {content_item}")
                raise TypeError("Expected a dictionary for content_item in generate_summary.")
            
            query = state['query']
            logging.debug(f"Generating summary for source: {source}")
            prompt = f"Summarize the following content to answer the question: {query}, mention the source: {source}   \n\n <content> {content[:500]}... </content>"
            logging.chat(f"generate_summary is sending data to model: {prompt}")
            page_summary = simple_model.invoke(prompt) # May need advanced model
            logging.chat(f"generate_summary received data from model: {page_summary.content}")
            logging.debug(f"Summary generated (first 1000 characters): {page_summary.content[:1000]}...")
            return {"page_summaries": [page_summary.content]}

        @classmethod
        def continue_to_summarise_node(cls, state):
            logging.debug("Entering continue_to_summarise_node")
            if 'page_content' not in state or not state['page_content']:
                logging.error("page_content is missing or empty in state")
                return []
            logging.debug(f"Page content before summarization: {state['page_content']}")
            
            return [Send("Generate Summary", {
                "content": {
                    "page_content": p['page_content'],
                    "metadata": p.get("metadata", {})
                },
                "query": state['messages'][0].content
            }) for p in state['page_content'] if isinstance(p, dict)]

        @classmethod
        def final_result_node(cls, state):
            logging.debug("Entering final_result_node")
            messages = state['messages']
            question = messages[-1]
            context = state['page_summaries']
            logging.debug(f"Question: {question}")
            logging.debug(f"Number of context summaries: {len(context)}")
            prompt = ChatPromptTemplate.from_messages(
                [
                    ("system", PerplexityClone.FINAL_NODE_SYSTEM_PROMPT),
                    ("human", PerplexityClone.FINAL_NODE_PROMPT),
                ]
            )
            input = {"question": question, "context": context}
            formatted_prompt = prompt.format_messages(**input)
            logging.debug(f"Formatted prompt for final response: {formatted_prompt}")
            response = advanced_model.invoke(formatted_prompt)
            logging.debug(f"Final response generated (first 500 characters): {response.content[:500]}...")
            return {"messages": [response]}

        @staticmethod
        async def search(queries):
            logging.debug("Entering search method")
            apiUrl = os.getenv("SEARXNG_API_URL_DEV")
            if not apiUrl:
                raise ValueError("SEARXNG_API_URL_DEV is not set in the environment variables")

            use_cache = os.getenv("DEV_MODE", "true").lower() == "false"

            async with aiohttp.ClientSession() as session:
                results = []
                for query in queries:
                    logging.debug(f"Searching for query: {query}")

                    # Check cache for existing results only if DEV_MODE is false
                    if use_cache:
                        cache_key = f"searxng_search:{query}"
                        cached_result = get_cached_results(cache_key)
                        if cached_result:
                            logging.info(f"Found cached search result for query: {query}")
                            results.append(cached_result)
                            continue

                    try:
                        params = {
                            'q': query,
                            'format': 'json',
                            'categories': 'general',
                            'engines': os.getenv('SEARXNG_ENGINES', 'google,bing,duckduckgo'),
                            'time_range': os.getenv('SEARXNG_TIME_RANGE', ''),
                            'safesearch': os.getenv('SEARXNG_SAFESEARCH', '0'),
                        }
                        url = f"{apiUrl}/search?{urlencode(params)}"
                        async with session.get(url) as response:
                            if response.status != 200:
                                raise Exception(f"SearXNG API error: {response.status}")
                            data = await response.json()
                            if 'results' not in data:
                                logging.warning(f"No results found for query: {query}")
                                search_results = []
                            else:
                                search_results = data['results'][:3]  # Limit to top 3 results
                            
                            results.append(search_results)
                            
                            # Cache the result only if DEV_MODE is false
                            if use_cache:
                                set_cached_results(cache_key, search_results)
                            
                            logging.debug(f"Raw API response for query '{query}': {data}")
                    except Exception as e:
                        logging.error(f"Error in search for query {query}: {str(e)}")
                        results.append([])  # Add an empty list for failed queries

            return results

# Create an instance of PerplexityClone
perplexity_clone_instance = PerplexityClone()

# Construct the graph using the class methods
perplexity_clone = StateGraph(PerplexityClone.OverallState)
perplexity_clone.add_node('Additional Questions', PerplexityClone.OverallState.additional_questions_node)
perplexity_clone.add_node('Ask', PerplexityClone.OverallState.ask_node)
perplexity_clone.add_node('New Question', PerplexityClone.OverallState.new_question_node)
perplexity_clone.add_node('Query Generator', PerplexityClone.OverallState.search_query_node)
perplexity_clone.add_node('Search Results', PerplexityClone.OverallState.search_results_node)
perplexity_clone.add_node('Web Scraper', PerplexityClone.OverallState.web_scrape_node)
perplexity_clone.add_node('Generate Summary', PerplexityClone.OverallState.generate_summary)
perplexity_clone.add_node('Final Result', PerplexityClone.OverallState.final_result_node)

perplexity_clone.set_entry_point('Additional Questions')
perplexity_clone.set_finish_point('Final Result')

perplexity_clone.add_conditional_edges('Additional Questions', PerplexityClone.OverallState.where_to_go, {'proceed': 'Query Generator', 'ask': 'Ask'})
perplexity_clone.add_edge('Ask', 'New Question')
perplexity_clone.add_edge('New Question', 'Query Generator')
perplexity_clone.add_edge('Query Generator', 'Search Results')
perplexity_clone.add_edge('Search Results', 'Web Scraper')
perplexity_clone.add_conditional_edges('Web Scraper', PerplexityClone.OverallState.continue_to_summarise_node, ['Generate Summary'])
perplexity_clone.add_edge('Generate Summary', 'Final Result')

# Compile the graph
perplexity_clone_graph = perplexity_clone.compile(checkpointer=MemorySaver(), interrupt_after=["Ask"])

# Export the graph and OverallState
OverallState = PerplexityClone.OverallState

# Export the graph and OverallState
__all__ = ["perplexity_clone_graph", "OverallState"]
