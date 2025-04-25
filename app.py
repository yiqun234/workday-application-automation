import time

import selenium.common.exceptions as selenium_exceptions
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver import Keys
from selenium.webdriver.firefox.service import Service as FirefoxService
from selenium.webdriver.chrome.service import Service as ChromeService
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.support.wait import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from utils import (check_element_text_is_empty,
                   convert_strdate_to_numbpad_keys,
                   today_date_in_keys)
import yaml

from webdrivers_installer import install_web_driver


class PageStep:
    def __init__(self, action, params, options=None):
        self.action = action
        self.params = params
        if options is None:
            self.options = {}
        else:
            self.options = options


class WorkdayAutofill:
    def __init__(self, application_link, resume_path):
        self.application_link = application_link
        self.resume_path = resume_path
        self.driver = WorkdayAutofill.create_webdriver("chrome")
        self.resume_data = self.load_resume()
        self.current_url = None
        self.ELEMENT_WAITING_TIMEOUT = 2

    @classmethod
    def create_webdriver(cls, browser_name):
        try:
            if browser_name.lower() == "firefox":
                driver = webdriver.Firefox()
            elif browser_name.lower() == "chrome":
                from webdriver_manager.chrome import ChromeDriverManager
                from selenium.webdriver.chrome.service import Service
                service = Service(ChromeDriverManager().install())
                driver = webdriver.Chrome(service=service)
            else:
                raise RuntimeError(f"{browser_name} is not supported !")
        except selenium_exceptions.WebDriverException:
            # trying to install the web driver if not installed in the system
            if browser_name.lower() == "firefox":
                web_driver_path = install_web_driver(requested_browser=browser_name)
                driver = webdriver.Firefox(service=FirefoxService(executable_path=web_driver_path))
            elif browser_name.lower() == "chrome":
                web_driver_path = install_web_driver(requested_browser=browser_name)
                driver = webdriver.Chrome(service=ChromeService(executable_path=web_driver_path))
            else:
                raise RuntimeError(f"{browser_name} is not supported !")
        else:
            return driver

    def load_resume(self):
        with open(self.resume_path) as resume:
            try:
                return yaml.safe_load(resume)
            except yaml.YAMLError as e:
                print(e)

    def load_work_experiences(self):
        try:
            works = self.resume_data["my-experience"]["work-experiences"]
            return [work_dict[f"work{idx}"] for idx, work_dict in enumerate(works, start=1)]
        except KeyError:
            raise ValueError("Something went wrong while parsing your resume.yml WORK-EXPERIENCE"
                             f" -> please review the works order !")

    def load_education_experiences(self):
        try:
            educations = self.resume_data["my-experience"]["education-experiences"]
            return [education_dict[f"education{idx}"] for idx, education_dict in enumerate(educations, start=1)]
        except KeyError:
            raise ValueError("Something went wrong while parsing your resume.yml EDUCATION-EXPERIENCES"
                             f" -> please review the educations order !")

    def load_languages(self):
        try:
            languages = self.resume_data["my-experience"]["languages"]
            return [language_dict[f"language{idx}"] for idx, language_dict in enumerate(languages, start=1)]
        except KeyError:
            raise ValueError("Something went wrong while parsing your resume.yml LANGUAGES"
                             f" -> please review the languages order !")

    def load_additional_information(self):
        try:
            return self.resume_data["additional-information"]
        except KeyError:
            raise ValueError("Something went wrong while parsing your resume.yml LANGUAGES"
                             f" -> please review the additional-information key !")

    def locate_and_fill(self, element_xpath, input_data, kwoptions):
        if not input_data:
            return False
        if not kwoptions.get("required"):
            try:
                element = self.driver.find_element(By.XPATH, element_xpath)
            except selenium_exceptions.NoSuchElementException:
                # skip if element is not in the page
                return False
        else:
            try:
                element = WebDriverWait(self.driver, self.ELEMENT_WAITING_TIMEOUT).until(
                    EC.presence_of_element_located((By.XPATH, element_xpath)))
            except (selenium_exceptions.NoSuchElementException, selenium_exceptions.TimeoutException):
                raise RuntimeError(
                    f"Cannot locate element '{element_xpath}' in the following page : {self.driver.current_url}"
                )
        if kwoptions.get("only_if_empty") and not check_element_text_is_empty(element):
            # quit if the element is already filled
            return False
        # fill date MM/YYYY
        if "YYYY" in element_xpath:
            date_keys = convert_strdate_to_numbpad_keys(input_data)
            element.send_keys(date_keys)
        else:
            self.driver.execute_script(
                'arguments[0].value="";', element)
            element.send_keys(input_data)
        if kwoptions.get("press_enter"):
            element.send_keys(Keys.ENTER)
        return True

    def locate_dropdown_and_fill(self, element_xpath, input_data, kwoptions):
        if not kwoptions.get("required"):
            try:
                element = self.driver.find_element(By.XPATH, element_xpath)
            except selenium_exceptions.NoSuchElementException:
                # skip if element is not in the page
                return False
        else:
            try:
                element = WebDriverWait(self.driver, self.ELEMENT_WAITING_TIMEOUT).until(
                    EC.presence_of_element_located((By.XPATH, element_xpath)))
            except (selenium_exceptions.NoSuchElementException, selenium_exceptions.TimeoutException):
                raise RuntimeError(
                    f"Cannot locate element '{element_xpath}' in the following page : {self.driver.current_url}"
                )

        self.driver.execute_script("arguments[0].click();", element)
        element.send_keys(input_data)
        if kwoptions.get("value_is_pattern"):
            select_xpath = f'//div[contains(text(),"{input_data}")]'
        else:
            select_xpath = f'//div[text()="{input_data}"]'
        try:
            choice = WebDriverWait(self.driver, self.ELEMENT_WAITING_TIMEOUT).until(
                EC.presence_of_element_located((By.XPATH, select_xpath)))
        except (selenium_exceptions.NoSuchElementException, selenium_exceptions.TimeoutException):
            raise RuntimeError(
                f"Cannot locate option: >'{input_data}'< in the following drop down : {element_xpath}"
                " Check your resume data"
            )
        else:
            self.driver.execute_script("arguments[0].click();", choice)
            return True

    def locate_and_click(self, button_xpath, kwoptions):
        try:
            clickable_element = WebDriverWait(self.driver, self.ELEMENT_WAITING_TIMEOUT).until(
                EC.presence_of_element_located((By.XPATH, button_xpath)))
        except (selenium_exceptions.NoSuchElementException, selenium_exceptions.TimeoutException):
            if not kwoptions.get("required"):
                return False
            raise RuntimeError(
                f"Cannot locate submit button '{button_xpath}' in the following page : {self.driver.current_url}"
            )
        else:
            self.driver.execute_script("arguments[0].click();", clickable_element)
            return True

    def locate_and_upload(self, button_xpath, file_location):
        try:
            element = WebDriverWait(self.driver, self.ELEMENT_WAITING_TIMEOUT).until(
                EC.presence_of_element_located((By.XPATH, button_xpath)))
        except (selenium_exceptions.NoSuchElementException, selenium_exceptions.TimeoutException):
            raise RuntimeError(
                f"Cannot locate button '{button_xpath}' in the following page : {self.driver.current_url}"
            )
        else:
            element.send_keys(file_location)
            return True

    def locate_and_drag_drop(self, element1_xpath, element2_xpath):
        try:
            element1 = WebDriverWait(self.driver, self.ELEMENT_WAITING_TIMEOUT).until(
                EC.presence_of_element_located((By.XPATH, element1_xpath)))
            element2 = WebDriverWait(self.driver, self.ELEMENT_WAITING_TIMEOUT).until(
                EC.presence_of_element_located((By.XPATH, element2_xpath)))
        except (selenium_exceptions.NoSuchElementException, selenium_exceptions.TimeoutException):
            raise RuntimeError(
                f"Cannot locate '{element1_xpath}' or '{element2_xpath}'  in the following page : "
                f"{self.driver.current_url}"
            )
        else:
            action = ActionChains(self.driver)
            action.drag_and_drop(element1, element2).perform()
            return True

    def execute_instructions(self, instructions):
        idx = 0 # 从第一个元素开始
        while idx < len(instructions): # 当索引还在列表范围内时循环
            page_step = instructions[idx] # 获取当前指令
            print(page_step.params)
            status = False # Default status

            # --- 执行指令逻辑 (和之前一样) ---
            if page_step.action == "LOCATE_AND_FILL":
                status = self.locate_and_fill(*page_step.params, page_step.options)
            elif page_step.action == "LOCATE_AND_CLICK":
                status = self.locate_and_click(*page_step.params, page_step.options)
            elif page_step.action == "LOCATE_DROPDOWN_AND_FILL":
                status = self.locate_dropdown_and_fill(*page_step.params, page_step.options)
            elif page_step.action == "LOCATE_AND_UPLOAD":
                status = self.locate_and_upload(*page_step.params, page_step.options)
            elif page_step.action == "LOCATE_AND_DRAG_DROP":
                status = self.locate_and_drag_drop(*page_step.params, page_step.options)
            else:
                raise RuntimeError(f"Unknown instruction: {page_step.action} \n"
                                   f" called with params : {page_step.params} \n "
                                   f"and options : {page_step.options} ")
            # --- 指令执行结束 ---

            # 如果指令执行成功
            if status:
                instructions.pop(idx)
                # 不增加idx，因为下一个元素已经移动到了当前idx的位置
            else:
                # 如果指令执行失败，或者没有执行成功，则移动到下一个索引
                idx += 1

    def create_account(self):
        """尝试创建一个新账号"""
        print("[INFO] 尝试创建账号")

        # 点击adventure按钮
        self.execute_instructions([
            PageStep(action="LOCATE_AND_CLICK",
                     params=['//a[@data-automation-id="adventureButton"]'],
                     options={"required": False})
        ])

        # 点击applyManually按钮
        self.execute_instructions([
            PageStep(action="LOCATE_AND_CLICK",
                     params=['//a[@data-automation-id="applyManually"]'],
                     options={"required": False})
        ])

        # 等待email输入框出现
        self.wait_for_element_presence('//input[@data-automation-id="email"]', 10)

        # 填写邮箱和密码
        email = self.resume_data["account"]["email"]
        password = self.resume_data["account"]["password"]

        self.execute_instructions([
            PageStep(action="LOCATE_AND_FILL",
                     params=['//input[@data-automation-id="email"]', email],
                     options={"required": True}),
            PageStep(action="LOCATE_AND_FILL",
                     params=['//input[@data-automation-id="password"]', password],
                     options={"required": True}),
            PageStep(action="LOCATE_AND_FILL",
                     params=['//input[@data-automation-id="verifyPassword"]', password],
                     options={"required": True})
        ])

        # 如果存在创建账号的复选框，则勾选
        create_account_checkbox = '//input[@data-automation-id="createAccountCheckbox"]'
        if self.check_element_exist(create_account_checkbox):
            self.execute_instructions([
                PageStep(action="LOCATE_AND_CLICK",
                         params=[create_account_checkbox],
                         options={"required": False})
            ])

        # 点击创建账号按钮
        time.sleep(2)
        self.execute_instructions([
            PageStep(action="LOCATE_AND_CLICK",
                     params=['//div[@data-automation-id="click_filter"]'],  # Changed from signInButton to signInLink
            )
        ])

        # 等待 5 秒
        time.sleep(5)
        print("[INFO] 创建账号结束")

        # 检查是否有错误消息（账号可能已存在）
        result = not self.check_element_exist('//div[@data-automation-id="errorMessage"]')
        if result:
            print("[INFO] 账号创建成功")
        else:
            print("[INFO] 账号创建失败，可能已存在")
        return result

    def login(self):
        """登录账号，成功返回True"""
        print("[INFO] 开始登录")
        # 点击登陆链接 (Now using signInLink button)
        self.execute_instructions([
            PageStep(action="LOCATE_AND_CLICK",
                     params=['//button[@data-automation-id="signInLink"]'], # Changed from signInButton to signInLink
                     options={"required": True})
        ])
        email_xpath = '//text()[contains(.,"Email Address")]/following::input[1]'
        password_xpath = '//text()[contains(.,"Password")]/following::input[1]'
        submit_xpath = '//div[contains(@aria-label,"Sign In")]'
        email = self.resume_data["account"]["email"]
        password = self.resume_data["account"]["password"]
        self.execute_instructions([
            # locate email input & fill
            PageStep(action="LOCATE_AND_FILL",
                     params=[email_xpath, email],
                     options={
                         "required": True
                     }),
            # locate password input & fill
            PageStep(action="LOCATE_AND_FILL",
                     params=[password_xpath, password],
                     options={
                         "required": True
                     })
        ])

        # submit
        time.sleep(2)
        self.execute_instructions([
            PageStep(action="LOCATE_AND_CLICK",
                     params=[submit_xpath])
        ])
        
        # 等待登录完成
        time.sleep(5)
        print("[INFO] 登录完成")
        
        # 验证登录成功 - 检查是否不再有登录按钮
        login_success = not self.check_element_exist('//button[@data-automation-id="signInLink"]')
        if login_success:
            print("[INFO] 登录成功")
        else:
            print("[INFO] 登录可能失败，请检查")
        
        return True  # 返回True让流程继续

    def fill_my_information_page(self):
        # Previous work
        # time.sleep(5)
        if self.resume_data["my-information"]["previous-work"]:
            previous_work_xpath = '//text()[contains(.,"former")]/following::input[1]'

        else:
            previous_work_xpath = '//text()[contains(.,"former")]/following::input[2]'

        # instructions List of ordered steps :
        # a list of (Action, HTML Xpath, Value, options ...)
        # options is not required
        instructions = [
            # How Did You Hear About Us
            (PageStep(action="LOCATE_AND_FILL",
                      params=['//div//text()[contains(., "How Did You Hear About Us?")]'
                              '/following::input[1]',
                              self.resume_data["my-information"]["source"]],
                      options={"press_enter": True})),
            # Previous work
            PageStep(action="LOCATE_AND_CLICK",
                     params=[previous_work_xpath]),
            # Country
            PageStep(action="LOCATE_DROPDOWN_AND_FILL",
                     params=['//div//text()[contains(., "Country")]'
                             '/following::button[@aria-haspopup="listbox"][1]',
                             self.resume_data["my-information"]["country"]]),
            # ****** Legal Name ******
            # First Name
            PageStep(action="LOCATE_AND_FILL",
                     params=['//div//text()[contains(., "First Name")]'
                             '/following::input[1]',
                             self.resume_data["my-information"]["first-name"]]),
            # Last Name
            PageStep(action="LOCATE_AND_FILL",
                     params=['//div//text()[contains(., "Last Name")]'
                             '/following::input[1]',
                             self.resume_data["my-information"]["last-name"]]),
            # ****** Address ******
            # Line 1
            PageStep(action="LOCATE_AND_FILL",
                     params=['//div[@aria-labelledby="Address-section"]'
                             '//text()[contains(., "Address Line 1")]'
                             '/following::input[1]',
                             self.resume_data["my-information"]["address-line"]]),
            # City
            # PageStep(action="LOCATE_AND_FILL",
            #          params=['//div[@aria-labelledby="Address-section"]'
            #                  '//text()[contains(., "City")]'
            #                  '/following::input[1]',
            #                  self.resume_data["my-information"]["city"]]),
            # 中国是下拉的
            # PageStep(action="LOCATE_DROPDOWN_AND_FILL",
            #          params=['//div[@aria-labelledby="Address-section"]'
            #                  '//text()[contains(., "City")]'
            #                  '/following::button[@aria-haspopup="listbox"][1]',
            #                  self.resume_data["my-information"]["city"]]),

            # State
            PageStep(action="LOCATE_DROPDOWN_AND_FILL",
                     params=['//div[@aria-labelledby="Address-section"]'
                             '//text()[contains(., "State")]'
                             '/following::button[@aria-haspopup="listbox"][1]',
                             self.resume_data["my-information"]["state"]]),
            # Zip
            PageStep(action="LOCATE_AND_FILL",
                     params=['//div[@aria-labelledby="Address-section"]'
                             '//text()[contains(., "Postal Code")]'
                             '/following::input[1]',
                             self.resume_data["my-information"]["zip"]]),

            # ****** Phone ******
            # Device Type
            PageStep(action="LOCATE_DROPDOWN_AND_FILL",
                     params=['//div//text()[contains(., "Phone Device Type")]'
                             '/following::button[@aria-haspopup="listbox"][1]',
                             self.resume_data["my-information"]["phone-device-type"]]),
            # Phone Code
            PageStep(action="LOCATE_AND_FILL",
                     params=['//div//text()[contains(., "Country Phone Code")]/following::input[1]',
                             self.resume_data["my-information"]["phone-code-country"]],
                     options={'press_enter': True}),
            # Number
            PageStep(action="LOCATE_AND_FILL",
                     params=['//div//text()[contains(., "Phone Number")]/following::input[1]',
                             self.resume_data["my-information"]["phone-number"]]),
            # Extension
            PageStep(action="LOCATE_AND_FILL",
                     params=['//div//text()[contains(., "Phone Extension")]'
                             '/following::input[1]',
                             self.resume_data["my-information"]["phone-extension"]]),
            # # Submit
            PageStep(action="LOCATE_AND_CLICK",
                     params=['//div//button[contains(text(),"Save and Continue")]']),
        ]

        self.execute_instructions(instructions)
        # 等待页面加载
        time.sleep(5)
        return True

    def add_works(self, instructions):
        # check if there are work experiences
        if len(self.load_work_experiences()):
            # 首先检查页面上是否已存在工作经历输入框
            if not self.check_element_exist('//*[contains(text(),"Work Experience 1")]'):
                # 只有在不存在输入框时才点击添加按钮
                instructions.append(PageStep(action="LOCATE_AND_CLICK",
                                            params=[
                                                '//div[@aria-labelledby="Work-Experience-section"]//button[@data-automation-id="add-button"]']))
            else:
                print("[INFO] Work Experience section already exists, skipping add button")
            
            # fill work experiences
            works_count = len(self.load_work_experiences())
            for idx, work in enumerate(self.load_work_experiences(), start=1):
                print(idx)
                instructions += [
                    # Job title
                    PageStep(action="LOCATE_AND_FILL",
                             params=[f'//div[@aria-labelledby="Work-Experience-{idx}-panel"]//text()[contains(.,"Job Title")]/following::Input[1]',
                                     work["job-title"]]),
                    # Company
                    PageStep(action="LOCATE_AND_FILL",
                             params=[f'//div[@aria-labelledby="Work-Experience-{idx}-panel"]//text()[contains(.,"Company")]/following::Input[1]',
                                     work["company"]]),
                    # Location
                    PageStep(action="LOCATE_AND_FILL",
                             params=[f'//div[@aria-labelledby="Work-Experience-{idx}-panel"]//text()[contains(.,"Location")]/following::Input[1]',
                                     work["location"]]),
                    # From Date
                    PageStep(action="LOCATE_AND_FILL",
                             params=[f'//div[@aria-labelledby="Work-Experience-{idx}-panel"]//text()[contains(.,"From")]/following::input[contains(@aria-valuetext, "MM") or contains(@aria-valuetext, "YYYY")][1]',
                                     work["from"]]),
                    # Description
                    PageStep(action="LOCATE_AND_FILL",
                             params=[f'//div[@aria-labelledby="Work-Experience-{idx}-panel"]//text()[contains(.,"Role Description")]/following::textarea[1]',
                                     work["description"]])
                ]
                # Current work
                if not work["current-work"]:
                    # To Date
                    instructions.append(PageStep(action="LOCATE_AND_FILL",
                                                 params=[f'//div[@aria-labelledby="Work-Experience-{idx}-panel"]//text()[contains(.,"To")]/following::input[contains(@aria-valuetext, "MM") or contains(@aria-valuetext, "YYYY") ][1]',
                                                         work["to"]]))

                else:
                    instructions.append(
                        PageStep(action="LOCATE_AND_CLICK",
                                 params=[f'//div[@aria-labelledby="Work-Experience-{idx}-panel"]//label[contains(.,"I currently work here")]/following-sibling::div[1]//input[@type="checkbox" and @aria-checked="false"]']),
                    )
                # check if more work experiences remaining
                if not idx == works_count:
                    # 检查下一个工作经历是否已存在
                    if not self.check_element_exist(f'//*[contains(text(),"Work Experience {idx+1}")]'):
                        # 只有在不存在下一个工作经历输入框时才点击添加按钮
                        instructions.append(
                            PageStep(action="LOCATE_AND_CLICK",
                                    params=['//div[@aria-labelledby="Work-Experience-section"]//button[@data-automation-id="add-button"]']),
                        )
                    else:
                        print(f"[INFO] Work Experience {idx+1} already exists, skipping add button")
        return instructions

    def add_education(self, instructions):
        # check if there are education experiences
        if len(self.load_education_experiences()):
            # 首先检查页面上是否已存在教育经历输入框
            if not self.check_element_exist('//*[contains(text(),"Education 1")]'):
                # 只有在不存在输入框时才点击添加按钮
                instructions.append(
                    PageStep(action="LOCATE_AND_CLICK",
                            params=['//div[@aria-labelledby="Education-section"]//button[@data-automation-id="add-button"]'])
                )
            else:
                print("[INFO] Education section already exists, skipping add button")

            # fill work experiences
            educations_count = len(self.load_education_experiences())
            for idx, education in enumerate(self.load_education_experiences(), start=1):
                instructions += [
                    # School or University
                    PageStep(action="LOCATE_AND_FILL",
                             params=[f'//text()[contains(.,"Education {idx}")]'
                                     f'/following::text()[contains(.,"School or University")]'
                                     f'/following::input[1]',
                                     education["university"]]),
                    # Degree
                    PageStep(action="LOCATE_DROPDOWN_AND_FILL",
                             params=[f'//text()[contains(.,"Education {idx}")]'
                                     f'/following::text()[contains(.,"Degree")]'
                                     f'/following::button[1]',
                                     education["degree"]],
                             options={
                                 "value_is_pattern": True
                             }),
                    # Field of study
                    PageStep(action="LOCATE_AND_FILL",
                             params=[f'//text()[contains(.,"Education {idx}")]'
                                     f'/following::text()[contains(.,"Field of Study")]'
                                     f'/following::input[1]',
                                     education["field-of-study"]],
                             options={"press_enter": True}),
                    # Gpa
                    PageStep(action="LOCATE_AND_FILL",
                             params=[f'//text()[contains(.,"Education {idx}")]'
                                     '/following::text()[contains(.,"Overall Result")]/'
                                     'following::input[1]',
                                     education["gpa"]]),
                    # From date
                    PageStep(action="LOCATE_AND_FILL",
                             params=[f'//text()[contains(.,"Education {idx}")]'
                                     '/following::text()[contains(.,"From")]/'
                                     'following::input[contains(@aria-valuetext, "MM")'
                                     ' or contains(@aria-valuetext, "YYYY") ][1]',
                                     education["from"]]),

                    # To date
                    PageStep(action="LOCATE_AND_FILL",
                             params=[f'//text()[contains(.,"Education {idx}")]'
                                     f'/following::text()[contains(.,"To")]'
                                     f'/following::input[contains(@aria-valuetext, "MM")'
                                     f' or contains(@aria-valuetext, "YYYY") ][1]',
                                     education["to"]]),
                ]

                # check if more education experiences remaining
                if not idx == educations_count:
                    # 检查下一个教育经历是否已存在
                    if not self.check_element_exist(f'//*[contains(text(),"Education {idx+1}")]'):
                        # 只有在不存在下一个教育经历输入框时才点击添加按钮
                        instructions.append(PageStep(action="LOCATE_AND_CLICK",
                                                    params=['//div[@aria-labelledby="Education-section"]//button[@data-automation-id="add-button"]']))
                    else:
                        print(f"[INFO] Education {idx+1} already exists, skipping add button")
        return instructions

    def add_resume(self, instructions):
        instructions += [
            # delete the old resume if exist
            PageStep(action="LOCATE_AND_CLICK",
                     params=['//button[@data-automation-id="delete-file"]']),
            PageStep(action="LOCATE_AND_FILL",
                     params=['//input[@data-automation-id="file-upload-input-ref"]',
                             self.resume_data["my-experience"]["resume"]]),
        ]
        return instructions

    def check_element_exist(self, xpath):
        """检查页面上是否存在指定XPath的元素"""
        try:
            element = self.driver.find_element(By.XPATH, xpath)
        except (selenium_exceptions.NoSuchElementException, selenium_exceptions.TimeoutException):
            return False
        else:
            return bool(element)

    def check_section_exist(self, section_name):
        """检查页面上是否存在特定名称的部分"""
        xpath = f'//h3[contains(text(),"{section_name}")]'
        result = self.check_element_exist(xpath)
        if not result:
            print(f"[INFO] Skipping section {section_name} because it doesn't exist")
        return result

    def add_languages(self, instructions):
        # CHECK IF LANGUAGES SECTION EXIST
        if not self.check_section_exist("Languages"):
            return instructions
        
        languages_data = self.load_languages()
        if len(languages_data):
            # 首先检查页面上是否已存在语言输入框
            if not self.check_element_exist('//*[contains(text(),"Languages 1")]'):
                # 只有在不存在输入框时才点击添加按钮
                instructions.append(
                    PageStep(action="LOCATE_AND_CLICK",
                             # Assuming a container similar to other sections
                             params=['//div[@aria-labelledby="Languages-section"]//button[contains(text(),"Add")][1]']) 
                )
            else:
                 print("[INFO] Languages section already exists, skipping add button")

            # fill Languages
            languages_count = len(languages_data)
            for idx, language in enumerate(languages_data, start=1):
                # Fluent ? (Assuming fluent checkbox needs similar relative path if applicable)
                if language["fluent"]:
                    instructions.append(
                        PageStep(action="LOCATE_AND_CLICK",
                                 params=[f'//text()[contains(.,"Languages {idx}")]'
                                         f'/following::text()[contains(.,"I am fluent in this language")]'
                                         f'/following::input[1]']))
                instructions += [
                    # Language
                    PageStep(action="LOCATE_DROPDOWN_AND_FILL",
                             params=[f'//text()[contains(.,"Languages {idx}")]'
                                     f'/following::text()[contains(.,"Language")]'
                                     f'/following::button[1]',
                                     language["language"]],
                             options={"value_is_pattern": True}),
                    # Reading
                    PageStep(action="LOCATE_DROPDOWN_AND_FILL",
                             params=[f'//text()[contains(.,"Languages {idx}")]'
                                     f'/following::text()[contains(.,"Level")]'
                                     f'/following::button[1]',
                                     language["level"]],
                             options={"value_is_pattern": True}),

                    # Reading
                    PageStep(action="LOCATE_DROPDOWN_AND_FILL",
                             params=[f'//text()[contains(.,"Languages {idx}")]'
                                     f'/following::text()[contains(.,"Reading Proficiency")]'
                                     f'/following::button[1]',
                                     language["comprehension"]],
                             options={"value_is_pattern": True}),

                    # Speaking
                    PageStep(action="LOCATE_DROPDOWN_AND_FILL",
                            params=[f'//text()[contains(.,"Languages {idx}")]'
                                    f'/following::text()[contains(.,"Speaking Proficiency")]'
                                    f'/following::button[1]',
                                    language["overall"]],
                            options={"value_is_pattern": True}),
                    # Translation
                    PageStep(action="LOCATE_DROPDOWN_AND_FILL",
                             params=[f'//text()[contains(.,"Languages {idx}")]'
                                     f'/following::text()[contains(.,"Translation")]'
                                     f'/following::button[1]',
                                     language["reading"]],
                             options={"value_is_pattern": True}),
                    # Writing
                    PageStep(action="LOCATE_DROPDOWN_AND_FILL",
                             params=[f'//text()[contains(.,"Languages {idx}")]'
                                     f'/following::text()[contains(.,"Writing Proficiency")]'
                                     f'/following::button[1]',
                                     language["writing"]],
                             options={"value_is_pattern": True}),
                ]

                # check if more languages remaining
                if not idx == languages_count:
                    # 检查下一个语言输入框是否已存在
                    if not self.check_element_exist(f'//*[contains(text(),"Languages {idx+1}")]'):
                         # 只有在不存在下一个输入框时才点击添加按钮
                        instructions.append(
                            PageStep(action="LOCATE_AND_CLICK",
                                     # Assuming the "Add Another" button is within the current language item's scope
                                     params=[f'//text()[contains(.,"Languages {idx}")]/following::button[contains(text(),"Add Another")][1]']), # Example XPath, might need refinement
                        )
                    else:
                        print(f"[INFO] Languages {idx+1} already exists, skipping add another button")
        return instructions

    def add_websites(self, instructions):
        if not self.check_section_exist("Websites"):
            return instructions

        websites_data = self.resume_data["my-experience"]["websites"]
        websites_count = len(websites_data)
        if websites_count:
            # 首先检查页面上是否已存在网站输入框
            # Using a more specific check based on expected label/input structure
            if not self.check_element_exist('//*[contains(text(),"Professional Websites(s) 1")]'): 
                # 只有在不存在输入框时才点击添加按钮
                instructions.append(
                    PageStep(action="LOCATE_AND_CLICK",
                            # Assuming a container similar to other sections
                             params=['//div[@aria-labelledby="Websites-section"]//button[contains(text(),"Add")][1]']), # Example XPath, might need refinement

                )
            else:
                 print("[INFO] Websites section already exists, skipping add button")

            # fill websites
            for idx, website in enumerate(websites_data, start=1):
                instructions += [
                    # Website
                    PageStep(action="LOCATE_AND_FILL",
                             params=[
                                 f'//text()[contains(.,"Professional Websites(s) {idx}")]'
                                    '/following::text()[contains(.,"URL")]/'
                                    'following::input[1]',
                                 website])
                ]
                # check if more websites remaining
                if not idx == websites_count:
                     # 检查下一个网站输入框是否已存在
                    if not self.check_element_exist(f'//*[contains(text(),"Professional Websites(s) {idx+1}")]'):
                        # 只有在不存在下一个输入框时才点击添加按钮
                        instructions.append(
                            PageStep(action="LOCATE_AND_CLICK",
                                     # Assuming the "Add Another" button is within the current website item's scope
                                     params=[f'//text()[contains(.,"Professional Websites(s) {idx}")]/following::button[contains(text(),"Add Another")][1]']), # Example XPath, might need refinement
                        )
                    else:
                         print(f"[INFO] Website {idx+1} already exists, skipping add another button")

        return instructions

    def fill_my_experience_page(self):
        instructions = []
        steps = {
            "WORKS": self.add_works,
            "EDUCATION": self.add_education,
            "LANGUAGES": self.add_languages,
            "RESUME": self.add_resume,
            "WEBSITES": self.add_websites,
        }
        for step_name, action in steps.items():
            print(f"[INFO] adding {step_name}")
            instructions = action(instructions)

        self.execute_instructions(instructions=instructions)
        # 等待页面加载, 等等简历上传的
        time.sleep(5)
        self.execute_instructions([
            PageStep(action="LOCATE_AND_CLICK",
                     params=[
                         '//button[contains(text(),"Save and Continue")]'])
        ])
        time.sleep(5) # 等待跳转
        return True

    def fill_my_additional_information(self):
        if self.check_application_review_reached():
            print("[INFO] Application completed ! click submit")
        else:
            print("[INFO] Please complete the required information and ")
        # fill the available information until it reach review page
        information = self.load_additional_information()
        instructions = [
            # 18 yo ?
            PageStep(action="LOCATE_DROPDOWN_AND_FILL",
                     params=[f'//text()[contains(.,"Are you at least 18")]'
                             f'/following::button[1]',
                             information["above-18-year"]]),
            # high school or GED ?
            PageStep(action="LOCATE_DROPDOWN_AND_FILL",
                     params=[f'//text()[contains(.,"Do you have a high school")]'
                             f'/following::button[1]',
                             information["high-school-diploma"]]),
            # authorized to work ?
            PageStep(action="LOCATE_DROPDOWN_AND_FILL",
                     params=[f'//text()[contains(.,"authorized to work")]'
                             f'/following::button[1]',
                             information["work-authorization"]]),
            # visa sponsorship ?
            PageStep(action="LOCATE_DROPDOWN_AND_FILL",
                     params=[f'//text()[contains(.,"sponsorship")]'
                             f'/following::button[1]',
                             information["visa-sponsorship"]]),
            # Serving military ?
            PageStep(action="LOCATE_DROPDOWN_AND_FILL",
                     params=[f'//text()[contains(.,"Have you served")]'
                             f'/following::button[1]',
                             information["served-military"]]),
            # military spouse ?
            PageStep(action="LOCATE_DROPDOWN_AND_FILL",
                     params=[f'//text()[contains(.,"former military spouse")]'
                             f'/following::button[1]',
                             information["military-spouse"]]),
            # Protected veteran
            PageStep(action="LOCATE_DROPDOWN_AND_FILL",
                     params=[f'//text()[contains(.,"Protected Veteran")]'
                             f'/following::button[1]',
                             information["protected-veteran"]]),
            # ethnicity
            PageStep(action="LOCATE_DROPDOWN_AND_FILL",
                     params=[f'//text()[contains(.,"ethnicity category")]'
                             f'/following::button[1]',
                             information["ethnicity"]]),
            # Gender / self identification
            PageStep(action="LOCATE_DROPDOWN_AND_FILL",
                     params=[f'//text()[contains(.,"Gender")]'
                             f'/following::button[1]',
                             information["self-identification"]]),

            # Accept Terms ?
            PageStep(action="LOCATE_AND_CLICK"
                     , params=[
                        f'//text()[contains(.,"I consent to")]'
                        f'/following::input[1]'
                     ],
                     options={"required": False}
                    ),



            ## SELF Identify
            # Language
            PageStep(action="LOCATE_DROPDOWN_AND_FILL",
                     params=[f'//h2[contains(text(),"Self Identify")]'
                             f'/following::text()[contains(.,"Language")]'
                             f'/following::button[1]',
                             information["language"]]),
            # Name
            PageStep(action="LOCATE_AND_FILL",
                     params=[f'//h2[contains(text(),"Self Identify")]'
                             f'/following::text()[contains(.,"Name")]'
                             f'/following::input[1]',
                             self.resume_data["my-information"]["first-name"] +
                             " " +
                             self.resume_data["my-information"]["last-name"]
                             ]),
            # Today's Date
            PageStep(action="LOCATE_AND_FILL",
                     params=[f'//h2[contains(text(),"Self Identify")]'
                             f'/following::text()[contains(.,"Date")]'
                             f'/following::input[1]',
                             today_date_in_keys()]),
        ]

        self.execute_instructions(instructions=instructions)
        # 等待页面加载
        time.sleep(5)

        self.execute_instructions([
            PageStep(action="LOCATE_AND_CLICK",
                     params=[
                         f'//h2[contains(text(),"Self Identify")]'
                         f'/following::label[contains(text(),"No,")]'
                     ],
                     )
        ])
        time.sleep(1)

        self.execute_instructions([
            PageStep(action="LOCATE_AND_CLICK",
                     params=[
                         '//button[contains(text(),"Save and Continue")]'])
        ])
        time.sleep(10000000)
        return True

    def check_application_review_reached(self):
        try:
            xpath = '//h2[contains(text(),"Review")]'
            element = self.driver.find_element(By.XPATH, xpath)
        except selenium_exceptions.NoSuchElementException:
            return False
        else:
            return bool(element)

    def check_errors_in_page(self):
        try:
            xpath = '//div[contains(text(),"Error")]'
            element = self.driver.find_element(By.XPATH, xpath)
        except selenium_exceptions.NoSuchElementException:
            return False
        else:
            return bool(element)

    def identify_current_page(self):
        """识别当前页面类型，返回页面类型标识符"""
        try:
            # 检查是否在登录页面
            if self.check_element_exist('//button[@data-automation-id="signInLink"]'):
                return "登录页面"
            
            # 检查各个主要部分
            if self.check_element_exist('//h2[contains(text(),"My Information")]'):
                return "个人信息页面"
            
            if self.check_element_exist('//div[@aria-labelledby="Work-Experience-section"]'):
                return "工作经历页面"
                
            if self.check_element_exist('//div[@aria-labelledby="Education-section"]'):
                return "教育经历页面"
                
            if self.check_element_exist('//h2[contains(text(),"Self Identify")]'):
                return "附加信息页面"
                
            if self.check_element_exist('//h2[contains(text(),"Review")]'):
                return "审核页面"
                
            # 检查是否在创建账号页面
            if self.check_element_exist('//input[@data-automation-id="email"]'):
                return "创建账号页面"
            
        except Exception as e:
            print(f"[错误] 页面识别失败: {e}")
        
        return "未知页面"

    def process_current_page(self):
        """处理当前页面，自动选择处理方法或提示人工操作"""
        # 识别当前页面
        page_type = self.identify_current_page()
        print(f"[信息] 当前识别页面类型: {page_type}")
        
        # 根据页面类型选择处理方法
        if page_type == "登录页面":
            result = self.login()
            # 登录后等待页面跳转
            time.sleep(5)
            # 检查是否页面变化
            new_page_type = self.identify_current_page()
            if new_page_type == page_type:
                print("[警告] 登录后页面类型未变化，可能需要人工干预")
                return self.handle_manual_operation()
            else:
                print(f"[信息] 页面已变化为: {new_page_type}")
                return True
        elif page_type == "创建账号页面":
            result = self.create_account()
            if not result:
                # 如果创建账号失败，尝试登录
                print("[信息] 尝试登录")
                return self.login()
            return True
        elif page_type == "个人信息页面":
            print("[信息] 开始填写个人信息")
            result = self.fill_my_information_page()
            print("[信息] 个人信息填写完成")
            return result
        elif page_type == "工作经历页面":
            print("[信息] 开始填写工作经历")
            result = self.fill_my_experience_page()
            print("[信息] 工作经历填写完成")
            return result
        elif page_type == "附加信息页面":
            print("[信息] 开始填写附加信息")
            result = self.fill_my_additional_information()
            print("[信息] 附加信息填写完成")
            return result
        elif page_type == "审核页面":
            print("[完成] 已到达申请审核页面")
            return self.submit_application()
        else:
            # 未知页面，需要人工干预
            print(f"[警告] 检测到未知页面类型: {page_type}")
            return self.handle_manual_operation()

    def handle_manual_operation(self):
        """处理需要人工干预的情况"""
        print("\n[需要人工干预] 无法自动识别或处理当前页面")
        print("请手动完成当前页面操作，完成后输入下一步操作:")
        print("1 - 继续自动处理")
        print("2 - 尝试提交表单并继续")
        print("3 - 退出程序")
        
        choice = input("请选择操作 [1/2/3]: ")
        
        if choice == "1":
            return True
        elif choice == "2":
            # 尝试点击保存并继续按钮
            try:
                self.execute_instructions([
                    PageStep(action="LOCATE_AND_CLICK",
                            params=['//button[contains(text(),"Save and Continue")]'],
                            options={"required": False})
                ])
                time.sleep(3)  # 等待页面加载
                return True
            except Exception as e:
                print(f"[错误] 无法提交表单: {e}")
                return False
        else:
            print("[退出] 用户选择退出程序")
            return False

    def submit_application(self):
        """提交最终申请"""
        print("[操作] 尝试提交申请...")
        try:
            self.execute_instructions([
                PageStep(action="LOCATE_AND_CLICK",
                        params=['//button[contains(text(),"Submit")]'],
                        options={"required": False})
            ])
            print("[成功] 申请已提交!")
            return True
        except Exception as e:
            print(f"[错误] 提交申请失败: {e}")
            return self.handle_manual_operation()

    def start_application(self):
        """开始申请流程"""
        self.driver.get(self.application_link)
        print("[开始] 访问申请链接...")
        
        # 先执行固定的登录注册流程
        print("[INFO] 执行登录/注册流程")
        
        # 首先尝试创建账号
        account_created = self.create_account()
        
        # 如果创建账号失败（可能是已存在），则尝试登录
        if not account_created:
            self.login()
        
        print("[INFO] 登录/注册完成，开始自动填写表单")
        time.sleep(5)  # 等待页面加载
        
        # 循环处理剩余的表单页面
        max_attempts = 10  # 防止无限循环
        attempts = 0
        
        while attempts < max_attempts:
            attempts += 1
            # 等待页面加载
            time.sleep(3)
            
            # 检查是否已完成申请
            if self.check_application_review_reached():
                print("[完成] 申请已到达审核页面")
                self.submit_application()
                break
            
            # 识别并处理当前页面
            page_type = self.identify_current_page()
            print(f"[信息] 当前识别页面类型: {page_type}")
            
            # 根据页面类型处理表单
            if page_type == "个人信息页面":
                print("[信息] 填写个人信息")
                self.fill_my_information_page()
            elif page_type == "工作经历页面":
                print("[信息] 填写工作经历")
                self.fill_my_experience_page()
            elif page_type == "附加信息页面":
                print("[信息] 填写附加信息")
                self.fill_my_additional_information()
            else:
                # 未知表单页面，询问用户
                print(f"[警告] 检测到未知页面类型: {page_type}")
                if not self.handle_manual_operation():
                    break
        
        if attempts >= max_attempts:
            print("[警告] 达到最大尝试次数，可能存在循环或页面识别问题")
            self.handle_manual_operation()
        
        print("[结束] 申请流程已完成")

    def wait_for_element_presence(self, xpath, timeout=None, description=None):
        """
        等待指定XPath的元素在页面上出现
        
        参数:
            xpath (str): 要查找的元素的XPath
            timeout (int, optional): 超时时间(秒)，如果不指定则使用默认值
            description (str, optional): 元素描述，用于日志记录
            
        返回:
            WebElement: 如果找到元素，返回该元素
            None: 如果超时未找到元素
            
        示例:
            element = self.wait_for_element_presence('//button[@id="submit"]')
            if element:
                element.click()
        """
        if timeout is None:
            timeout = self.ELEMENT_WAITING_TIMEOUT
            
        if description is None:
            description = f"XPath: {xpath}"
            
        try:
            print(f"[等待] 等待元素加载 ({description})")
            element = WebDriverWait(self.driver, timeout).until(
                EC.presence_of_element_located((By.XPATH, xpath))
            )
            print(f"[成功] 元素已加载 ({description})")
            return element
        except (selenium_exceptions.NoSuchElementException, selenium_exceptions.TimeoutException) as e:
            print(f"[错误] 等待元素超时 ({description}): {e}")
            return None
            
    def wait_for_element_clickable(self, xpath, timeout=None, description=None):
        """
        等待指定XPath的元素在页面上出现并且可点击
        
        参数:
            xpath (str): 要查找的元素的XPath
            timeout (int, optional): 超时时间(秒)，如果不指定则使用默认值
            description (str, optional): 元素描述，用于日志记录
            
        返回:
            WebElement: 如果找到可点击元素，返回该元素
            None: 如果超时未找到可点击元素
            
        示例:
            element = self.wait_for_element_clickable('//button[@id="submit"]')
            if element:
                element.click()
        """
        if timeout is None:
            timeout = self.ELEMENT_WAITING_TIMEOUT
            
        if description is None:
            description = f"XPath: {xpath}"
            
        try:
            print(f"[等待] 等待元素可点击 ({description})")
            element = WebDriverWait(self.driver, timeout).until(
                EC.element_to_be_clickable((By.XPATH, xpath))
            )
            print(f"[成功] 元素可点击 ({description})")
            return element
        except (selenium_exceptions.NoSuchElementException, selenium_exceptions.TimeoutException) as e:
            print(f"[错误] 等待元素可点击超时 ({description}): {e}")
            return None

    # exit
    # self.driver.quit()


if __name__ == '__main__':
    # 注册链接
    # APPLICATION_LINK = "https://kcura.wd1.myworkdayjobs.com/en-US/External_Career_Site/job/Remote-United-States/Advanced-Software-Engineer_25-0013/apply/applyManually?source=LinkedIn"
    APPLICATION_LINK = "https://kcura.wd1.myworkdayjobs.com/External_Career_Site/job/Remote-United-States/Advanced-Software-Engineer_25-0013?source=LinkedIn"
    RESUME_PATH = "resume.yml"
    s = WorkdayAutofill(
        application_link=APPLICATION_LINK,
        resume_path=RESUME_PATH
    )
    print(today_date_in_keys())
    print(s.load_resume())
    print(s.load_additional_information())

    s.start_application()
    print("hello")
