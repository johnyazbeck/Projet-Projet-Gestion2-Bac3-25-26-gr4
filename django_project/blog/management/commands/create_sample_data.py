from django.core.management.base import BaseCommand
from blog.models import Category, ICTComponent
from django.contrib.auth.models import User

class Command(BaseCommand):
    help = 'Creates sample data for the ICT knowledge base'

    def handle(self, *args, **kwargs):
        # Create technical categories
        categories_data = [
            {'name': 'Infrastructure', 'description': 'Servers, virtualization, cloud computing'},
            {'name': 'Network', 'description': 'Routing, switching, firewall, VPN'},
            {'name': 'Systems', 'description': 'Operating systems Windows/Linux'},
            {'name': 'Databases', 'description': 'MySQL, PostgreSQL, MongoDB, Oracle'},
            {'name': 'Security', 'description': 'Cybersecurity, authentication, encryption'},
            {'name': 'Applications', 'description': 'Business applications, software'},
            {'name': 'Support', 'description': 'User support, helpdesk'},
            {'name': 'Development', 'description': 'Development, APIs, integration'},
        ]

        # Create ICT components
        components_data = [
            # Servers
            {'name': 'Apache Web Server', 'component_type': 'server', 'description': 'Apache HTTP web server'},
            {'name': 'Nginx Server', 'component_type': 'server', 'description': 'Nginx web server'},
            {'name': 'VMware ESXi', 'component_type': 'server', 'description': 'VMware hypervisor'},
            
            # Network
            {'name': 'Cisco Router', 'component_type': 'router', 'description': 'Cisco ISR router'},
            {'name': 'HP Switch', 'component_type': 'switch', 'description': 'Manageable HP switch'},
            {'name': 'Fortinet Firewall', 'component_type': 'firewall', 'description': 'FortiGate firewall'},
            
            # Databases
            {'name': 'MySQL', 'component_type': 'database', 'description': 'MySQL database'},
            {'name': 'PostgreSQL', 'component_type': 'database', 'description': 'PostgreSQL database'},
            {'name': 'MongoDB', 'component_type': 'database', 'description': 'NoSQL MongoDB database'},
            
            # Applications
            {'name': 'Odoo CRM', 'component_type': 'application', 'description': 'Open source CRM Odoo'},
            {'name': 'SAP ERP', 'component_type': 'application', 'description': 'SAP Business One ERP'},
            {'name': 'Office 365', 'component_type': 'software', 'description': 'Microsoft Office 365 suite'},
            
            # Cloud
            {'name': 'AWS EC2', 'component_type': 'cloud', 'description': 'AWS EC2 cloud service'},
            {'name': 'Azure VM', 'component_type': 'cloud', 'description': 'Azure virtual machines'},
        ]

        self.stdout.write('Creating technical categories...')
        for cat_data in categories_data:
            category, created = Category.objects.get_or_create(
                name=cat_data['name'],
                defaults={'description': cat_data['description']}
            )
            if created:
                self.stdout.write(f'✓ Category created: {category.name}')

        self.stdout.write('Creating ICT components...')
        for comp_data in components_data:
            component, created = ICTComponent.objects.get_or_create(
                name=comp_data['name'],
                defaults={
                    'component_type': comp_data['component_type'],
                    'description': comp_data['description']
                }
            )
            if created:
                self.stdout.write(f'✓ Component created: {component.name}')

        self.stdout.write(
            self.style.SUCCESS('Sample data created successfully!')
        )
