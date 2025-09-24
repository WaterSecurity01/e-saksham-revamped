import os
import zipfile
from lxml import etree

from app.models import Course

class SCORMParser:
    def __init__(self, upload_path, package_path, package_id, title, description):
        self.upload_path = upload_path
        self.package_path = package_path
        self.manifest_path = None
        self.manifest_identifier = None
        self.manifest_title = None
        self.package_id = package_id
        self.launch_url = 'None'
        self.title = title
        self.description = description
        self.scorm_version = None
        self.duplicate_package_path = None

    def to_json(self):
        return {
            "upload_path":self.upload_path,
            "package_path":self.package_path,
            "manifest_path":self.manifest_path,
            "manifest_identifier":self.manifest_identifier,
            "manifest_title":self.manifest_title,
            "package_id":self.package_id,
            "launch_url":self.launch_url,
            "title":self.title,
            "description":self.description,
            "scorm_version":self.scorm_version,
            "duplicate_package_path":self.duplicate_package_path
        }

    def extract_package(self):
        with zipfile.ZipFile(self.upload_path, 'r') as zip_ref:
            zip_ref.extractall(self.package_path)

        self.manifest_path = os.path.join(self.package_path, 'imsmanifest.xml')
        if not os.path.exists(self.manifest_path):
            raise FileNotFoundError(f"Manifest not found: {self.manifest_path}")
        return self._parse_manifest()

    def _parse_manifest(self):
        tree = etree.parse(self.manifest_path)
        root = tree.getroot()

        # Setup namespaces
        nsmap = {
            'imscp': 'http://www.imsproject.org/xsd/imscp_rootv1p1p2',
            'adlcp': 'http://www.adlnet.org/xsd/adlcp_rootv1p2',
            'imsmd': 'http://www.imsglobal.org/xsd/imsmd_rootv1p2p1',
            'default': root.nsmap[None] if None in root.nsmap else ''
        }

        # Find SCORM version
        schema_version = root.xpath('//imscp:metadata/imscp:schemaversion', namespaces=nsmap)
        self.scorm_version = schema_version[0].text.strip() if schema_version else '1.2'

        # Get launch URL from <resources>
        resource_elems = root.xpath('//imscp:resources/imscp:resource[@adlcp:scormtype="sco"]', namespaces=nsmap)
        if resource_elems[0]:
            if 'href' in resource_elems[0].attrib:
                self.launch_url = resource_elems[0].attrib['href']
        else:
            self.launch_url = 'index_lms.html'

        # Title (fetch from nested LOM section, SCORM 1.2 style)
        title_elem = root.xpath('//imscp:metadata/imsmd:lom/imsmd:general/imsmd:title/imsmd:langstring', namespaces=nsmap)
        self.manifest_title = title_elem[0].text if title_elem[0].text else 'SCORM Course'

        # Unique Identifier (fetch from nested LOM section, SCORM 1.2 style)
        organization_item = root.xpath('//imscp:organizations/imscp:organization/imscp:item', namespaces=nsmap)[0]
        self.manifest_identifier = organization_item.attrib['identifierref'] if organization_item.attrib['identifierref'] else None

        # Check for package duplication
        identifier_exist = None
        if self.manifest_identifier:
            identifier_exist = Course.find_by_identifier(self.manifest_identifier)
        
        # if duplicate remove extracted file and return nothing
        if identifier_exist:
            self.duplicate_package_path=identifier_exist.package_path

        # Description (optional)
        # desc_elem = root.xpath('//imscp:metadata/imsmd:lom/imsmd:general/imsmd:description/imsmd:langstring', namespaces=nsmap)
        # self.description = desc_elem.text if desc_elem else 'No Description'

        return self.to_json()

        # return {
        #     "scorm_version": self.scorm_version,
        #     "title": self.title,
        #     "description": self.description,
        #     "launch_url": self.launch_url
        # }