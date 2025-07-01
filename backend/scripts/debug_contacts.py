#!/usr/bin/env python3
"""
Contact Debug Script

This script helps debug why certain contacts (like Aneta Giza) are missing
from our contact sync by testing different People API parameters.
"""

import sys
import os
import json
from dotenv import load_dotenv

# Add the backend directory to the path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Load environment variables
load_dotenv()

from composio import ComposioToolSet, Action

def test_different_contact_sources():
    """Test different ways to fetch contacts from Google People API"""
    composio_toolset = ComposioToolSet()
    
    results = {}
    
    print("🔍 Testing different contact retrieval methods...")
    print("=" * 60)
    
    # Test 1: Standard GMAIL_GET_CONTACTS (what we're currently using)
    print("\n1️⃣  Testing GMAIL_GET_CONTACTS (standard method)")
    try:
        result = composio_toolset.execute_action(
            action=Action.GMAIL_GET_CONTACTS,
            params={
                "resource_name": "people/me",
                "person_fields": "names,emailAddresses,phoneNumbers,metadata",
                "page_token": None
            }
        )
        
        if result.get('successful', False):
            data = result.get('data', {})
            if 'response_data' in data:
                connections = data['response_data'].get('connections', [])
                total_items = data['response_data'].get('totalItems', 0)
            else:
                connections = data.get('connections', [])
                total_items = len(connections)
            
            results['get_contacts'] = {
                'total_items': total_items,
                'fetched_count': len(connections),
                'sample_names': [
                    conn.get('names', [{}])[0].get('displayName', 'No Name') 
                    for conn in connections[:5] if conn.get('names')
                ]
            }
            print(f"   ✅ Success: {len(connections)} contacts (total: {total_items})")
            print(f"   📝 Sample names: {results['get_contacts']['sample_names']}")
        else:
            results['get_contacts'] = {'error': result.get('error', 'Unknown error')}
            print(f"   ❌ Failed: {result.get('error', 'Unknown error')}")
    
    except Exception as e:
        results['get_contacts'] = {'error': str(e)}
        print(f"   ❌ Exception: {str(e)}")
    
    # Test 2: GMAIL_SEARCH_PEOPLE with different parameters
    search_tests = [
        {"name": "Primary contacts only", "other_contacts": False},
        {"name": "Including other contacts", "other_contacts": True},
    ]
    
    for i, test in enumerate(search_tests, 2):
        print(f"\n{i}️⃣  Testing GMAIL_SEARCH_PEOPLE - {test['name']}")
        try:
            result = composio_toolset.execute_action(
                action=Action.GMAIL_SEARCH_PEOPLE,
                params={
                    "query": "Giza",  # Search specifically for Giza
                    "pageSize": 30,
                    "person_fields": "names,emailAddresses,phoneNumbers,metadata",
                    "other_contacts": test["other_contacts"]
                }
            )
            
            if result.get('successful', False):
                data = result.get('data', {})
                # Handle different possible response structures
                people = []
                if 'response_data' in data:
                    people = data['response_data'].get('results', [])
                    if people:
                        people = [item.get('person', {}) for item in people]
                else:
                    people = data.get('people', [])
                
                found_names = [
                    person.get('names', [{}])[0].get('displayName', 'No Name') 
                    for person in people if person.get('names')
                ]
                
                results[f'search_{test["other_contacts"]}'] = {
                    'count': len(people),
                    'found_names': found_names
                }
                print(f"   ✅ Success: {len(people)} people found")
                if found_names:
                    print(f"   📝 Found: {found_names}")
                else:
                    print(f"   📝 No matches for 'Giza'")
            else:
                results[f'search_{test["other_contacts"]}'] = {'error': result.get('error', 'Unknown error')}
                print(f"   ❌ Failed: {result.get('error', 'Unknown error')}")
        
        except Exception as e:
            results[f'search_{test["other_contacts"]}'] = {'error': str(e)}
            print(f"   ❌ Exception: {str(e)}")
    
    # Test 3: Search for "Aneta" to see if we find any Anetas
    print(f"\n4️⃣  Testing GMAIL_SEARCH_PEOPLE - Search for 'Aneta'")
    try:
        result = composio_toolset.execute_action(
            action=Action.GMAIL_SEARCH_PEOPLE,
            params={
                "query": "Aneta",
                "pageSize": 30,
                "person_fields": "names,emailAddresses,phoneNumbers,metadata",
                "other_contacts": True  # Include other contacts
            }
        )
        
        if result.get('successful', False):
            data = result.get('data', {})
            # Handle different possible response structures
            people = []
            if 'response_data' in data:
                people = data['response_data'].get('results', [])
                if people:
                    people = [item.get('person', {}) for item in people]
            else:
                people = data.get('people', [])
            
            found_anetas = []
            for person in people:
                if person.get('names'):
                    name = person['names'][0].get('displayName', 'No Name')
                    emails = person.get('emailAddresses', [])
                    email = emails[0]['value'] if emails else 'No Email'
                    found_anetas.append(f"{name} ({email})")
            
            results['search_aneta'] = {
                'count': len(people),
                'found_anetas': found_anetas
            }
            print(f"   ✅ Success: {len(people)} Anetas found")
            for aneta in found_anetas:
                print(f"   📝 Found: {aneta}")
        else:
            results['search_aneta'] = {'error': result.get('error', 'Unknown error')}
            print(f"   ❌ Failed: {result.get('error', 'Unknown error')}")
    
    except Exception as e:
        results['search_aneta'] = {'error': str(e)}
        print(f"   ❌ Exception: {str(e)}")
    
    # Summary
    print("\n" + "=" * 60)
    print("📊 SUMMARY")
    print("=" * 60)
    
    if 'get_contacts' in results and 'total_items' in results['get_contacts']:
        print(f"📧 Standard sync: {results['get_contacts']['fetched_count']}/{results['get_contacts']['total_items']} contacts")
    
    if 'search_True' in results:
        print(f"🔍 Search 'Giza' (with other contacts): {results['search_True'].get('count', 0)} found")
    
    if 'search_aneta' in results:
        print(f"🔍 Search 'Aneta' (with other contacts): {results['search_aneta'].get('count', 0)} found")
    
    print(f"\n💾 Full results saved to debug_results.json")
    
    # Save detailed results
    with open('debug_results.json', 'w') as f:
        json.dump(results, f, indent=2)
    
    return results

if __name__ == "__main__":
    print("🧪 Contact Debug Script")
    print("This script tests different ways to fetch contacts from Google People API")
    print("to help debug why some contacts might be missing.")
    print()
    
    results = test_different_contact_sources()
    
    print(f"\n🎯 RECOMMENDATIONS:")
    
    # Check if we found Giza in any method
    found_giza = False
    for key, result in results.items():
        if isinstance(result, dict) and 'found_names' in result:
            if any('Giza' in name for name in result['found_names']):
                found_giza = True
                break
        elif isinstance(result, dict) and 'found_anetas' in result:
            if any('Giza' in aneta for aneta in result['found_anetas']):
                found_giza = True
                break
    
    if found_giza:
        print("✅ Found Giza in at least one method - investigate why sync doesn't pick it up")
    else:
        print("❌ Giza not found in any method - contact might not be accessible via API")
    
    print("📋 Check debug_results.json for detailed analysis") 