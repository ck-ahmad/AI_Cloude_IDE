# Problems Faced During Development

## 1. Authentication Issues
- Forgot to protect some routes with login checks.
- Session data caused bugs after logout/login.

## 2. Database Confusion / XAMP Problem
- Mixed up `user_id` and `project_id` in a few places.
- Forgot to commit changes, so data didn’t save.
- Xamp problem lead to switch localhost DB to SQLlite DB

## 3. File Upload Problems
- File size tracking was inconsistent.
- Storage limits were sometimes calculated wrong.

## 4. Cloudinary Setup / Link Problems too
- Uploads failed due to missing or incorrect env variables.
- Folder structure had to be changed later.

## 5. Code Execution Bugs
- Infinite loops required adding execution timeouts.
- Temporary files were not deleted at first.

## 6. AI (Gemini) Integration / Model & api time out problem
- Used the wrong model name initially.
- Large prompts sometimes broke responses.

## 7. Code Organization(Fixed in next update )
- App file became too large.
- Some routes handle too many responsibilities.
